const fs = require('fs');

const replacements = [
  {
    file: 'src/app/[locale]/dashboard/employees/page.tsx',
    find: 'import { useRouter } from "next/navigation";',
    replace: 'import { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/app/[locale]/dashboard/employees/[id]/page.tsx',
    find: 'import { useParams, useRouter } from "next/navigation";',
    replace: 'import { useParams } from "next/navigation";\nimport { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/app/[locale]/dashboard/settings/integrations/callback/page.tsx',
    find: 'import { useSearchParams, useRouter } from "next/navigation";',
    replace: 'import { useSearchParams } from "next/navigation";\nimport { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/app/[locale]/login/page.tsx',
    find: 'import { useRouter } from "next/navigation";',
    replace: 'import { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/components/ai/AiChatWidget.tsx',
    find: 'import { useRouter } from "next/navigation";',
    replace: 'import { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/components/auth/auth-guard.tsx',
    find: 'import { useRouter } from "next/navigation";',
    replace: 'import { useRouter } from "@/i18n/routing";'
  },
  {
    file: 'src/components/layout/NotificationCenter.tsx',
    find: 'import { usePathname } from "next/navigation";',
    replace: 'import { usePathname } from "@/i18n/routing";'
  },
  {
    file: 'src/components/layout/Sidebar.tsx',
    find: 'import { usePathname } from "next/navigation";',
    replace: 'import { usePathname } from "@/i18n/routing";'
  },
  {
    file: 'src/components/layout/MobileSidebar.tsx',
    find: 'import { usePathname } from "next/navigation";',
    replace: 'import { usePathname } from "@/i18n/routing";'
  },
  {
    file: 'src/app/[locale]/dashboard/[...dynamic]/page.tsx',
    find: 'import { usePathname } from "next/navigation";',
    replace: 'import { usePathname } from "@/i18n/routing";'
  }
];

replacements.forEach(r => {
  if (fs.existsSync(r.file)) {
    let content = fs.readFileSync(r.file, 'utf8');
    content = content.replace(r.find, r.replace);
    fs.writeFileSync(r.file, content);
    console.log(`Updated ${r.file}`);
  } else {
    console.log(`Not found: ${r.file}`);
  }
});
