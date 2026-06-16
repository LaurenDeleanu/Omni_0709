import os, re

files = [
    r'c:\Users\Khazan\Documents\GitHub\Omnius\frontend\src\app\[locale]\page.tsx',
    r'c:\Users\Khazan\Documents\GitHub\Omnius\frontend\src\app\[locale]\pricing\page.tsx',
    r'c:\Users\Khazan\Documents\GitHub\Omnius\frontend\src\app\[locale]\careers\page.tsx',
    r'c:\Users\Khazan\Documents\GitHub\Omnius\frontend\src\app\[locale]\docs\page.tsx'
]

reps = {
    'text-slate-300': 'text-foreground/90',
    'text-slate-400': 'text-muted-foreground',
    'text-slate-500': 'text-muted-foreground',
    'text-slate-600': 'text-muted-foreground',
    'bg-white/5': 'bg-muted/20',
    'bg-white/10': 'bg-muted/30',
    'bg-white/3': 'bg-card',
    r'bg-white/\[0\.02\]': 'bg-muted/5',
    r'bg-white/\[0\.03\]': 'bg-muted/10',
    'border-white/5': 'border-border/50',
    'border-white/10': 'border-border',
    'border-white/20': 'border-border'
}

for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        for k, v in reps.items():
            content = re.sub(k, v, content)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
