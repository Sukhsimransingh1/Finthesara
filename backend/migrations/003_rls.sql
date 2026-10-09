-- Supabase Row-Level Security foundation.
-- Supabase service-role credentials bypass RLS and must remain server-side.

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claim_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calculations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.human_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
CREATE POLICY profiles_select_own ON public.profiles FOR SELECT USING (id = auth.uid());
DROP POLICY IF EXISTS profiles_insert_own ON public.profiles;
CREATE POLICY profiles_insert_own ON public.profiles FOR INSERT WITH CHECK (id = auth.uid());
DROP POLICY IF EXISTS profiles_update_own ON public.profiles;
CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS projects_owner_access ON public.projects;
CREATE POLICY projects_owner_access ON public.projects FOR ALL
    USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS research_runs_project_owner_access ON public.research_runs;
CREATE POLICY research_runs_project_owner_access ON public.research_runs FOR ALL
    USING (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()));

DROP POLICY IF EXISTS research_tasks_project_owner_access ON public.research_tasks;
CREATE POLICY research_tasks_project_owner_access ON public.research_tasks FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS documents_project_owner_access ON public.documents;
CREATE POLICY documents_project_owner_access ON public.documents FOR ALL
    USING (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()));

DROP POLICY IF EXISTS document_chunks_project_owner_access ON public.document_chunks;
CREATE POLICY document_chunks_project_owner_access ON public.document_chunks FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.documents d JOIN public.projects p ON p.id = d.project_id
        WHERE d.id = document_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.documents d JOIN public.projects p ON p.id = d.project_id
        WHERE d.id = document_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS sources_project_owner_access ON public.sources;
CREATE POLICY sources_project_owner_access ON public.sources FOR ALL
    USING (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()));

DROP POLICY IF EXISTS claims_project_owner_access ON public.claims;
CREATE POLICY claims_project_owner_access ON public.claims FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS calculations_project_owner_access ON public.calculations;
CREATE POLICY calculations_project_owner_access ON public.calculations FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS claim_evidence_project_owner_access ON public.claim_evidence;
CREATE POLICY claim_evidence_project_owner_access ON public.claim_evidence FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.claims c
        JOIN public.research_runs r ON r.id = c.research_run_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE c.id = claim_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.claims c
        JOIN public.research_runs r ON r.id = c.research_run_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE c.id = claim_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS verification_results_project_owner_access ON public.verification_results;
CREATE POLICY verification_results_project_owner_access ON public.verification_results FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.claims c
        JOIN public.research_runs r ON r.id = c.research_run_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE c.id = claim_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.claims c
        JOIN public.research_runs r ON r.id = c.research_run_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE c.id = claim_id AND p.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS human_reviews_project_owner_access ON public.human_reviews;
CREATE POLICY human_reviews_project_owner_access ON public.human_reviews FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = research_run_id AND p.owner_id = auth.uid()
    ))
    WITH CHECK (
        reviewer_id = auth.uid() AND EXISTS (
            SELECT 1 FROM public.research_runs r JOIN public.projects p ON p.id = r.project_id
            WHERE r.id = research_run_id AND p.owner_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS evaluation_datasets_owner_access ON public.evaluation_datasets;
CREATE POLICY evaluation_datasets_owner_access ON public.evaluation_datasets FOR ALL
    USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS evaluation_cases_dataset_owner_access ON public.evaluation_cases;
CREATE POLICY evaluation_cases_dataset_owner_access ON public.evaluation_cases FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.evaluation_datasets d
        WHERE d.id = evaluation_dataset_id AND d.owner_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.evaluation_datasets d
        WHERE d.id = evaluation_dataset_id AND d.owner_id = auth.uid()
    ));

DROP POLICY IF EXISTS evaluation_runs_dataset_owner_access ON public.evaluation_runs;
CREATE POLICY evaluation_runs_dataset_owner_access ON public.evaluation_runs FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.evaluation_datasets d
        WHERE d.id = evaluation_dataset_id AND d.owner_id = auth.uid()
    ))
    WITH CHECK (
        initiated_by = auth.uid() AND EXISTS (
            SELECT 1 FROM public.evaluation_datasets d
            WHERE d.id = evaluation_dataset_id AND d.owner_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS feedback_project_owner_access ON public.feedback;
CREATE POLICY feedback_project_owner_access ON public.feedback FOR ALL
    USING (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()))
    WITH CHECK (
        author_id = auth.uid() AND EXISTS (
            SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.owner_id = auth.uid()
        )
    );
