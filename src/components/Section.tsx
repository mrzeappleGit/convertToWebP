import type { ReactNode } from "react";

export function Section({ title, children, after }: { title: string; children?: ReactNode; after?: ReactNode }) {
  return (
    <div className="wwk-section">
      <div className="wwk-section-label">
        <span>{title}</span>
        {after}
      </div>
      {children}
    </div>
  );
}
