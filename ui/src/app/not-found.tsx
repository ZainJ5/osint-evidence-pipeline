import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

export default function NotFound() {
  return (
    <Card>
      <EmptyState
        icon={<FileQuestion className="size-5" />}
        title="Page not found"
        description="The page you requested does not exist."
        action={
          <Link href="/" className={buttonClasses("secondary")}>
            Back to dashboard
          </Link>
        }
      />
    </Card>
  );
}
