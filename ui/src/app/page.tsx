import Link from "next/link";
import { Plus } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { RunsTable } from "@/components/dashboard/runs-table";

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Analyses of candidates' public GitHub, Codeforces and LeetCode activity against job requirements."
        actions={
          <Link href="/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden />
            New analysis
          </Link>
        }
      />
      <RunsTable />
    </>
  );
}
