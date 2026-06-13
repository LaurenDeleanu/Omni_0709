import React from "react";
import { LucideIcon } from "lucide-react";

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, icon: Icon, action }: PageHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20 shrink-0">
              <Icon className="w-5 h-5" />
            </div>
          )}
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text text-transparent">
            {title}
          </h1>
        </div>
        {description && (
          <p className="text-muted-foreground mt-2 text-sm md:text-base max-w-2xl">
            {description}
          </p>
        )}
      </div>
      {action && (
        <div className="flex items-center gap-3 shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}
