"use client";

import { usePathname, useRouter } from "@/i18n/routing";
import { useLocale } from "next-intl";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Globe } from "lucide-react";

export function LocaleSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleLocaleChange = (newLocale: string | null) => {
    // router.replace accepts the pathname and options with the new locale
    if (newLocale) {
      router.replace(pathname, { locale: newLocale });
    }
  };

  return (
    <div className="flex items-center gap-2 px-2">
      <Globe className="w-4 h-4 text-muted-foreground" />
      <Select value={locale} onValueChange={handleLocaleChange}>
        <SelectTrigger className="w-[120px] h-8 text-xs border-border/50 bg-card/50">
          <SelectValue placeholder="Idioma / Language" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="es">Español</SelectItem>
          <SelectItem value="en">English</SelectItem>
          <SelectItem value="fr">Français</SelectItem>
          <SelectItem value="de">Deutsch</SelectItem>
          <SelectItem value="pt">Português</SelectItem>
          <SelectItem value="ar">العربية</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
