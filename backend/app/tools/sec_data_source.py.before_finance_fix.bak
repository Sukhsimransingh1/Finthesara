
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import get_settings
from app.tools.schemas import (
    FinancialDataQuery,
    FinancialDataResult,
    FinancialMetric,
    FinancialPeriod,
    MetricType,
)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

ANNUAL_FORMS = {"10-K", "20-F", "40-F"}
QUARTERLY_FORMS = {"10-Q"}

METRIC_CONCEPTS: dict[MetricType, tuple[str, ...]] = {
    MetricType.REVENUE: (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ),
    MetricType.OPERATING_EXPENSE: (
        "OperatingExpenses",
    ),
    MetricType.OPERATING_INCOME: (
        "OperatingIncomeLoss",
    ),
    MetricType.NET_INCOME: (
        "NetIncomeLoss",
        "ProfitLoss",
    ),
    MetricType.GROSS_PROFIT: (
        "GrossProfit",
    ),
    MetricType.EPS: (
        "EarningsPerShareDiluted",
        "EarningsPerShareBasic",
    ),
}


class SECDataSourceError(RuntimeError):
    """Raised when SEC data cannot be retrieved or parsed."""


class SECFinancialDataSource:
    """Retrieve reported financial metrics from SEC company facts."""

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        
        settings = get_settings()

        configured_user_agent = (
                user_agent
                if user_agent is not None
                else getattr(settings, "sec_user_agent", None)
                or os.getenv("SEC_USER_AGENT")
            )

        self.user_agent = (configured_user_agent or "").strip()
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }

        self._companies: list[dict[str, Any]] | None = None
        self._facts_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _normalize_company(value: str) -> str:
        normalized = re.sub(
            r"[^a-z0-9 ]",
            " ",
            value.casefold(),
        )
        normalized = " ".join(normalized.split())

        suffixes = {
            "inc",
            "incorporated",
            "corp",
            "corporation",
            "company",
            "co",
            "ltd",
            "limited",
            "plc",
        }

        parts = normalized.split()

        while parts and parts[-1] in suffixes:
            parts.pop()

        return " ".join(parts)

    def _get_json(self, url: str) -> dict[str, Any]:
        if (
            not self.user_agent
            or "your-email@example.com" in self.user_agent.lower()
        ):
            raise SECDataSourceError(
                "Configure SEC_USER_AGENT with your application name "
                "and a valid contact email."
            )
        try:
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SECDataSourceError(
                "Unable to retrieve financial data from the SEC."
            ) from exc

        if not isinstance(payload, dict):
            raise SECDataSourceError(
                "The SEC returned an unexpected response."
            )

        return payload

    def _load_companies(self) -> list[dict[str, Any]]:
        if self._companies is not None:
            return self._companies

        payload = self._get_json(SEC_TICKERS_URL)
        companies: list[dict[str, Any]] = []

        for item in payload.values():
            if not isinstance(item, dict):
                continue

            ticker = item.get("ticker")
            title = item.get("title")
            cik = item.get("cik_str")

            if (
                isinstance(ticker, str)
                and isinstance(title, str)
                and isinstance(cik, int)
            ):
                companies.append(
                    {
                        "ticker": ticker.upper(),
                        "title": title,
                        "cik": cik,
                    }
                )

        if not companies:
            raise SECDataSourceError(
                "The SEC company directory contained no usable records."
            )

        self._companies = companies
        return companies

    def _resolve_company(
        self,
        company: str,
    ) -> dict[str, Any] | None:
        companies = self._load_companies()
        query = company.strip().upper()

        # Prefer exact ticker matches.
        for item in companies:
            if item["ticker"] == query:
                return item

        normalized_query = self._normalize_company(company)

        if not normalized_query:
            return None

        matches = [
            item
            for item in companies
            if self._normalize_company(item["title"])
            == normalized_query
        ]

        # Avoid guessing when a company name is ambiguous.
        if len(matches) == 1:
            return matches[0]

        return None

    def _load_facts(
        self,
        cik: int,
    ) -> dict[str, Any]:
        if str(cik) in self._facts_cache:
            return self._facts_cache[str(cik)]

        url = SEC_FACTS_URL.format(cik=f"{cik:010d}")
        payload = self._get_json(url)

        facts = payload.get("facts")
        if not isinstance(facts, dict):
            raise SECDataSourceError(
                "The SEC response did not contain company facts."
            )

        us_gaap = facts.get("us-gaap")
        if not isinstance(us_gaap, dict):
            raise SECDataSourceError(
                "No US-GAAP facts were available for this company."
            )

        self._facts_cache[str(cik)] = us_gaap
        return us_gaap

    @staticmethod
    def _period_kind(
        period: FinancialPeriod,
    ) -> str:
        duration = (
            period.end_date - period.start_date
        ).days + 1

        return "annual" if duration >= 250 else "quarterly"

    @staticmethod
    def _eligible_duration(
        start: date,
        end: date,
        kind: str,
    ) -> bool:
        duration = (end - start).days + 1

        if kind == "annual":
            return 300 <= duration <= 400

        return 70 <= duration <= 110

    def _find_fact(
        self,
        *,
        us_gaap: dict[str, Any],
        metric: MetricType,
        requested_period: FinancialPeriod,
        kind: str,
    ) -> tuple[str, dict[str, Any], str] | None:
        allowed_forms = (
            ANNUAL_FORMS
            if kind == "annual"
            else QUARTERLY_FORMS
        )

        preferred_units = (
            ("USD/shares",)
            if metric == MetricType.EPS
            else ("USD",)
        )

        for concept in METRIC_CONCEPTS[metric]:
            concept_data = us_gaap.get(concept)

            if not isinstance(concept_data, dict):
                continue

            units = concept_data.get("units")
            if not isinstance(units, dict):
                continue

            for unit in preferred_units:
                facts = units.get(unit)

                if not isinstance(facts, list):
                    continue

                eligible: list[dict[str, Any]] = []

                for fact in facts:
                    if not isinstance(fact, dict):
                        continue

                    form = fact.get("form")
                    start_text = fact.get("start")
                    end_text = fact.get("end")
                    filed_text = fact.get("filed")
                    raw_value = fact.get("val")

                    if (
                        form not in allowed_forms
                        or not isinstance(start_text, str)
                        or not isinstance(end_text, str)
                        or not isinstance(filed_text, str)
                        or not isinstance(raw_value, (int, float))
                    ):
                        continue

                    try:
                        start = date.fromisoformat(start_text)
                        end = date.fromisoformat(end_text)
                    except ValueError:
                        continue

                    if not (
                        requested_period.start_date
                        <= end
                        <= requested_period.end_date
                    ):
                        continue

                    if not self._eligible_duration(
                        start,
                        end,
                        kind,
                    ):
                        continue

                    eligible.append(fact)

                if eligible:
                    # Prefer the most recently filed fact when a
                    # filing amendment reports the same period.
                    eligible.sort(
                        key=lambda item: (
                            str(item.get("end", "")),
                            str(item.get("filed", "")),
                        ),
                        reverse=True,
                    )
                    return concept, eligible[0], unit

        return None

    @staticmethod
    def _source_url(
        *,
        cik: int,
        fact: dict[str, Any],
    ) -> str:
        accession = fact.get("accn")

        if isinstance(accession, str) and accession:
            accession_path = accession.replace("-", "")
            return (
                f"{SEC_ARCHIVES_URL}/{cik}/"
                f"{accession_path}/"
            )

        return SEC_FACTS_URL.format(cik=f"{cik:010d}")

    def query(
        self,
        request: FinancialDataQuery,
    ) -> FinancialDataResult:
        company_info = self._resolve_company(request.company)

        if company_info is None:
            return FinancialDataResult(
                company=request.company,
                metric=request.metric,
                values=[],
                source_count=0,
            )

        cik = int(company_info["cik"])
        official_name = str(company_info["title"])
        ticker = str(company_info["ticker"])
        us_gaap = self._load_facts(cik)

        values: list[FinancialMetric] = []

        for requested_period in request.periods:
            kind = self._period_kind(requested_period)

            found = self._find_fact(
                us_gaap=us_gaap,
                metric=request.metric,
                requested_period=requested_period,
                kind=kind,
            )

            if found is None:
                continue

            concept, fact, unit = found

            try:
                value = Decimal(str(fact["val"]))
                start_date = date.fromisoformat(fact["start"])
                end_date = date.fromisoformat(fact["end"])
            except (
                InvalidOperation,
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            if not value.is_finite():
                continue

            fiscal_year = fact.get("fy")
            fiscal_period = fact.get("fp")

            if kind == "annual":
                # Comparative facts in a later SEC filing may carry the
                # later filing's fiscal-year metadata. Label by the
                # actual reporting period's end year instead.
                label = f"FY{end_date.year}"
            else:
                label = (
                    f"{fiscal_period} {fiscal_year}"
                    if fiscal_period and fiscal_year
                    else f"Quarter ending {end_date.isoformat()}"
                )

            accession = str(fact.get("accn", "unknown"))
            source_id = f"SEC:{ticker}:{accession}:{concept}"

            values.append(
                FinancialMetric(
                    company=official_name,
                    metric=request.metric,
                    period=FinancialPeriod(
                        label=label,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                    value=value,
                    currency="USD",
                    unit=unit,
                    source_id=source_id,
                    source_url=self._source_url(
                        cik=cik,
                        fact=fact,
                    ),
                )
            )

        values.sort(key=lambda item: item.period.end_date)

        return FinancialDataResult(
            company=official_name,
            metric=request.metric,
            values=values,
            source_count=len(
                {
                    item.source_id
                    for item in values
                    if item.source_id
                }
            ),
        )
