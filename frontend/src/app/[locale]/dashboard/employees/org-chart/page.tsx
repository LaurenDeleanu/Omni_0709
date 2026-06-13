"use client";

import { useEffect, useState } from "react";
import { UserAPI, Employee } from "@/lib/api";
import { Users, Briefcase, Building, Mail, Award, Search, ChevronDown, ChevronRight, CornerDownRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/routing";

interface TreeNode extends Employee {
  subordinates: TreeNode[];
}

export default function OrgChartPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  useEffect(() => {
    UserAPI.getEmployees()
      .then((data: any) => {
        setEmployees(data);
        // Expand all by default
        const initialExpanded: Record<string, boolean> = {};
        data.forEach((emp: Employee) => {
          initialExpanded[emp.id] = true;
        });
        setExpandedNodes(initialExpanded);
      })
      .catch((err) => console.error("Error loading employees for org chart:", err))
      .finally(() => setLoading(false));
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Build the hierarchical tree
  const buildTree = (list: Employee[]): TreeNode[] => {
    const map: Record<string, TreeNode> = {};
    const roots: TreeNode[] = [];

    // Initialize map
    list.forEach((item) => {
      map[item.id] = { ...item, subordinates: [] };
    });

    // Populate hierarchy
    list.forEach((item) => {
      const node = map[item.id];
      if (item.manager_id && map[item.manager_id]) {
        map[item.manager_id].subordinates.push(node);
      } else {
        // If no manager or manager not in list, it's a root
        roots.push(node);
      }
    });

    return roots;
  };

  // Departments list for filtering
  const departments = Array.from(new Set(employees.map((e) => e.department).filter(Boolean)));

  // Filtered employees
  const filteredEmployees = employees.filter((emp) => {
    const matchesSearch =
      (emp.full_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (emp.email || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (emp.role || "").toLowerCase().includes(searchTerm.toLowerCase());

    const matchesDept = departmentFilter === "all" || emp.department === departmentFilter;

    return matchesSearch && matchesDept;
  });

  const treeRoots = buildTree(filteredEmployees);

  // Render tree node recursively with premium aesthetics
  const renderNode = (node: TreeNode, level: number = 0) => {
    const hasSubordinates = node.subordinates.length > 0;
    const isExpanded = expandedNodes[node.id] !== false;
    const initials = node.full_name
      ? node.full_name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase()
      : "U";

    return (
      <div key={node.id} className="space-y-2">
        {/* User Node Card */}
        <div
          style={{ paddingLeft: `${level * 24}px` }}
          className="flex items-start gap-2 relative group"
        >
          {/* Connector Line Indentation */}
          {level > 0 && (
            <div className="absolute left-0 top-0 bottom-0 flex items-center justify-center pointer-events-none" style={{ left: `${(level - 1) * 24 + 10}px` }}>
              <div className="w-4 h-5 border-l-2 border-b-2 border-border/80 rounded-bl-lg -translate-y-3" />
            </div>
          )}

          {/* Toggle Expand Button */}
          <div className="w-6 h-10 flex items-center justify-center flex-shrink-0 z-10">
            {hasSubordinates ? (
              <button
                onClick={() => toggleExpand(node.id)}
                className="p-1 rounded-md hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-all duration-150"
              >
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
            ) : (
              <div className="w-1.5 h-1.5 rounded-full bg-border" />
            )}
          </div>

          {/* Branded Card */}
          <div className="flex-1 max-w-xl p-4 rounded-2xl border border-border/60 bg-card/65 backdrop-blur hover:border-indigo-600/30 hover:shadow-md transition-all duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              {/* Avatar circle */}
              <div className="h-11 w-11 rounded-2xl bg-indigo-600 flex items-center justify-center text-white font-extrabold shadow-md shadow-indigo-600/10 flex-shrink-0">
                {initials}
              </div>
              <div className="space-y-0.5 leading-tight">
                <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                  {node.full_name || node.email}
                  {node.is_active ? (
                    <span className="h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-emerald-500/10" />
                  ) : (
                    <span className="h-2 w-2 rounded-full bg-muted" />
                  )}
                </h4>
                <p className="text-xs text-indigo-600 font-semibold">{node.role || "Empleado"}</p>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-1">
                  <span className="flex items-center gap-0.5"><Building className="h-3 w-3" /> {node.department || "General"}</span>
                  <span>•</span>
                  <span className="flex items-center gap-0.5"><Mail className="h-3 w-3" /> {node.email}</span>
                </div>
              </div>
            </div>

            {/* Micro-actions */}
            <div className="flex items-center gap-2 self-end sm:self-center opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              <Link href="/dashboard/kudos">
                <Button size="sm" variant="outline" className="h-8 text-xs font-semibold flex items-center gap-1 border-indigo-600/20 text-indigo-600 hover:bg-indigo-600 hover:text-white">
                  <Award className="h-3.5 w-3.5" />
                  Kudos
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Subordinates */}
        {hasSubordinates && isExpanded && (
          <div className="space-y-2">
            {node.subordinates.map((sub) => renderNode(sub, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Jumbotron */}
      <div className="relative overflow-hidden rounded-3xl border border-border/40 bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 p-8 md:p-10 shadow-lg text-white">
        <div className="absolute right-0 top-0 translate-x-12 -translate-y-12 w-64 h-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5 w-fit">
              <Users className="h-3 w-3" /> Estructura Corporativa
            </span>
            <h2 className="text-3xl font-bold tracking-tight">Organigrama</h2>
            <p className="text-indigo-200 text-sm max-w-md">
              Explora la estructura de informes directos y la jerarquía organizativa de tu empresa de forma visual.
            </p>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="glass">
        <CardContent className="p-4 flex flex-col sm:flex-row gap-4 items-center justify-between">
          {/* Search */}
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Buscar por nombre, puesto o email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {/* Department Filter */}
          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <span className="text-xs font-semibold text-muted-foreground">Filtrar por Departamento:</span>
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="flex h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring cursor-pointer"
            >
              <option value="all">Todos los Departamentos</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Hierarchy Render Box */}
      <Card className="glass overflow-hidden p-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-2">
              <div className="h-8 w-8 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin mx-auto" />
              <p className="text-muted-foreground text-sm font-medium">Dibujando organigrama jerárquico...</p>
            </div>
          </div>
        ) : treeRoots.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground text-sm">
            No se encontraron empleados con los filtros aplicados.
          </div>
        ) : (
          <div className="space-y-4">
            {treeRoots.map((root) => renderNode(root))}
          </div>
        )}
      </Card>
    </div>
  );
}
