import { redirect } from "next/navigation";

export default function RunViewRedirect({
  params,
}: {
  params: { id: string; view: string };
}) {
  redirect(`/research/${params.id}`);
}
