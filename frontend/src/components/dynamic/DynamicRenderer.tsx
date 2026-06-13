"use client";

import { DynamicForm, FormSchema } from "./DynamicForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface TableSchema {
  type: "table";
  title?: string;
  columns: { key: string; label: string }[];
  data: any[];
}

interface LayoutSchema {
  type: "layout";
  direction?: "row" | "column";
  children: any[];
}

export function DynamicRenderer({ schema }: { schema: any }) {
  if (!schema) return null;
  switch (schema.type) {
    case "form":
      return (
        <Card>
          <CardContent className="pt-6">
            <DynamicForm schema={schema as FormSchema} onSubmit={(data) => console.log("Formulario enviado:", data)} />
          </CardContent>
        </Card>
      );
    
    case "table":
      const tblSchema = schema as TableSchema;
      return (
        <Card>
          {tblSchema.title && (
            <CardHeader>
              <CardTitle>{tblSchema.title}</CardTitle>
            </CardHeader>
          )}
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {tblSchema.columns?.map(c => <TableHead key={c.key}>{c.label}</TableHead>)}
                </TableRow>
              </TableHeader>
              <TableBody>
                {tblSchema.data?.map((row, idx) => (
                  <TableRow key={idx}>
                    {tblSchema.columns?.map(c => <TableCell key={c.key}>{row[c.key]}</TableCell>)}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      );
      
    case "layout":
      const layoutSchema = schema as LayoutSchema;
      return (
        <div className={`flex ${layoutSchema.direction === 'row' ? 'flex-row gap-6' : 'flex-col gap-6'}`}>
          {layoutSchema.children?.map((child, idx) => (
            <div key={idx} className={layoutSchema.direction === 'row' ? 'flex-1' : 'w-full'}>
              <DynamicRenderer schema={child} />
            </div>
          ))}
        </div>
      );
      
    case "page":
      return (
        <div className="space-y-6">
          {schema.title && <h1 className="text-3xl font-bold tracking-tight">{schema.title}</h1>}
          {schema.description && <p className="text-muted-foreground">{schema.description}</p>}
          <div className="mt-6">
            {schema.children?.map((child: any, idx: number) => (
              <DynamicRenderer key={idx} schema={child} />
            ))}
          </div>
        </div>
      );

    default:
      return <div className="p-4 border border-dashed border-red-500 text-red-500 rounded bg-red-50">Tipo de componente no soportado: {schema.type}</div>;
  }
}
