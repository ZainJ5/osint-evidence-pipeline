import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { NewAnalysisWizard } from "@/components/wizard/new-analysis-wizard";

export const metadata: Metadata = { title: "New analysis" };

export default function NewAnalysisPage() {
  return (
    <>
      <PageHeader
        title="New analysis"
        description="Verify a candidate's resume against their public GitHub, Codeforces and LeetCode activity."
      />
      <NewAnalysisWizard />
    </>
  );
}
