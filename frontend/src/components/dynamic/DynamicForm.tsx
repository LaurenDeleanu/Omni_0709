"use client";

import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface FieldSchema {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
}

export interface FormSchema {
  type: "form";
  title?: string;
  fields: FieldSchema[];
  submitLabel?: string;
}

interface DynamicFormProps {
  schema: FormSchema;
  onSubmit: (data: any) => void;
  defaultValues?: any;
}

export function DynamicForm({ schema, onSubmit, defaultValues }: DynamicFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues
  });
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {schema.title && <h3 className="text-lg font-medium">{schema.title}</h3>}
      {schema.fields?.map((field: FieldSchema, idx: number) => (
        <div key={idx} className="space-y-2">
          <Label htmlFor={field.name}>{field.label}</Label>
          <Input 
            id={field.name}
            type={field.type || "text"}
            {...register(field.name, { required: field.required })}
            className={errors[field.name] ? "border-red-500" : ""}
          />
          {errors[field.name] && <span className="text-xs text-red-500">Este campo es requerido</span>}
        </div>
      ))}
      <Button type="submit">{schema.submitLabel || "Guardar"}</Button>
    </form>
  );
}
