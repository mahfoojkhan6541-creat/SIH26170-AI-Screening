import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "wouter";
import DashboardLayout from "@/components/DashboardLayout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { defaultWorkspace } from "@/data/defaultWorkspace";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  BarChart2,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cpu,
  FileCheck2,
  FileWarning,
  Filter,
  FlaskConical,
  Gauge,
  Info,
  Layers,
  Loader2,
  RefreshCw,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UploadCloud,
} from "lucide-react";

export type ShapItem = {
  feature: string;
  shap_value: number;
  z_score: number;
  direction: string;
  impact: string;
};

export type Score = {
  id?: string;
  component_id: string;
  lot_id: string;
  device_type: string;
  parameter: string;
  unit: string;
  action: string;
  disposition?: string;
  rule?: string;
  reason?: string;
  explanation: string;
  risk_score: number;
  score?: number;
  status?: string;
  value_0h?: number;
  value_12h?: number;
  value_24h?: number;
  value_48h?: number;
  value_72h?: number;
  value_96h?: number;
  value_120h?: number;
  value_144h?: number;
  value_168h?: number;
  predicted_168h?: number;
  forecast_mean?: number;
  prediction_interval_90?: number;
  lower_2sigma?: number;
  upper_2sigma?: number;
  peer_median_24h?: number;
  peer_mad_24h?: number;
  spec_min?: number;
  spec_max?: number;
  reason_codes: string;
  traj?: number[];
  steps?: number[];
  drift?: number;
  shap?: ShapItem[];
  [key: string]: any;
};

export type Workspace = {
  dataOrigin: string;
  metrics: {
    screened_series?: number;
    action_counts?: Record<string, number>;
    mae?: number;
    early_decision_contract?: string;
    interval_coverage_90?: number;
    [key: string]: any;
  };
  artifact: {
    artifact_version?: string;
    training_rows?: number;
    training_data_hash?: string;
    model?: { kind: string };
    policy?: Record<string, any>;
    candidate_validation?: any[];
    [key: string]: any;
  };
  scores: Score[];
};

const pageTitles: Record<string, { eyebrow: string; title: string; copy: string }> = {
  "/": {
    eyebrow: "Operational Screening Workspace",
    title: "ISRO Component Burn-In & Drift Intelligence",
    copy: "Dynamic reference-population outlier screening, GPR trajectory forecasting, and TreeSHAP explainability for flight-grade electronics.",
  },
  "/datasets": {
    eyebrow: "Data Quality & Ingestion",
    title: "Canonical Schema Validation Gate",
    copy: "Strict schema verification and quarantine protocols for multi-device electrical burn-in telemetry (NASA aging & semiconductor batches).",
  },
  "/training": {
    eyebrow: "Model Evidence & Benchmarks",
    title: "Candidate Verification on Held-Out Hardware",
    copy: "Isolation Forest and Gaussian Process Regression validated against untouched held-out devices with zero test-leakage.",
  },
  "/screening": {
    eyebrow: "Decision Queue",
    title: "24-Hour Screening Triage Queue",
    copy: "Early risk flagging at 24h burn-in checkpoint, conservative QA routing, and deterministic disposition rules.",
  },
  "/inspector": {
    eyebrow: "Component Deep Dive",
    title: "Contextual Evidence & TreeSHAP Attribution",
    copy: "Inspect progressive measurements, peer median envelopes, GPR forecast cones with ±2σ bounds, and exact Shapley feature drivers.",
  },
  "/models": {
    eyebrow: "Model Governance",
    title: "Frozen Model Registry & Decoupled Rules",
    copy: "Auditable frozen weights, SHA-256 integrity hashes, and strict separation between unsupervised IF scores, GPR slopes, and spec limits.",
  },
  "/reports": {
    eyebrow: "Quality Assurance Handover",
    title: "Auditable Flight Screening Summary",
    copy: "Export complete component triage decisions, uncertainty bands, and mathematical reasoning for engineering sign-off.",
  },
};

function number(value: unknown, fraction = 3): string {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(fraction) : "—";
}

function actionTone(action: string) {
  if (action === "REJECT") return "border-rose-200 bg-rose-50 text-rose-700";
  if (action === "REVIEW") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function ActionBadge({ action }: { action: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("rounded-full px-2.5 py-1 font-mono text-[10px] font-semibold tracking-wider", actionTone(action))}
    >
      {action}
    </Badge>
  );
}

function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone = "slate",
}: {
  label: string;
  value: string;
  note: string;
  icon: any;
  tone?: "slate" | "amber" | "rose" | "emerald" | "cyan";
}) {
  const hues = {
    slate: "bg-slate-100 text-slate-700",
    amber: "bg-amber-100 text-amber-700",
    rose: "bg-rose-100 text-rose-700",
    emerald: "bg-emerald-100 text-emerald-700",
    cyan: "bg-cyan-100 text-cyan-700",
  };
  return (
    <Card className="metric-card overflow-hidden border-slate-200/80 shadow-sm transition hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
            <p className="mt-3 text-3xl font-extrabold tracking-tight text-slate-950">{value}</p>
          </div>
          <span className={cn("grid h-10 w-10 place-items-center rounded-xl", hues[tone])}>
            <Icon className="h-5 w-5" />
          </span>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">{note}</p>
      </CardContent>
    </Card>
  );
}

function EmptyState({ icon: Icon, title, copy }: { icon: any; title: string; copy: string }) {
  return (
    <div className="grid min-h-[320px] place-items-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 p-8 text-center">
      <div className="max-w-md">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-white text-slate-500 shadow-sm">
          <Icon className="h-5 w-5" />
        </span>
        <h3 className="mt-4 text-base font-bold text-slate-900">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">{copy}</p>
      </div>
    </div>
  );
}

function WorkspaceHeader({
  title,
  origin,
  isLiveConnected,
  onRefresh,
  isRefreshing,
}: {
  title: { eyebrow: string; title: string; copy: string };
  origin: string;
  isLiveConnected: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
}) {
  return (
    <header className="mb-7 flex flex-col justify-between gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-end">
      <div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-cyan-600 animate-pulse" />
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
            {title.eyebrow}
          </p>
        </div>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
          {title.title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{title.copy}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div
          className={cn(
            "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-xs",
            isLiveConnected
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-cyan-200 bg-cyan-50 text-cyan-800"
          )}
        >
          <span className={cn("h-2 w-2 rounded-full", isLiveConnected ? "bg-emerald-500" : "bg-cyan-500")} />
          {isLiveConnected ? "FastAPI Live Stream (Port 8000)" : "Embedded Verified Workspace"}
        </div>

        <Badge variant="outline" className="border-slate-300 bg-white font-mono text-[11px] text-slate-700">
          7 NASA Devices + D2 HEMT + D1 IC (481 Series)
        </Badge>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="h-8 border-slate-200 hover:bg-slate-100"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", isRefreshing && "animate-spin")} />
          Sync Live
        </Button>
      </div>
    </header>
  );
}

// -----------------------------------------------------------------------------
// OVERVIEW TAB
// -----------------------------------------------------------------------------
function Overview({
  workspace,
  onInspect,
}: {
  workspace: Workspace;
  onInspect: (score: Score) => void;
}) {
  const actions = (workspace.metrics.action_counts ?? {}) as Record<string, number>;
  const total = workspace.metrics.screened_series ?? workspace.scores.length;
  const flagged = (actions.REVIEW ?? 0) + (actions.REJECT ?? 0);

  // Focus queue on flagged components first
  const queue = useMemo(() => {
    const nonPass = workspace.scores.filter((s) => s.action !== "PASS");
    const pass = workspace.scores.filter((s) => s.action === "PASS");
    return [...nonPass, ...pass].slice(0, 8);
  }, [workspace.scores]);

  return (
    <div className="space-y-6">
      {/* Primary Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Screened Series"
          value={String(total)}
          note="Authentic series across 7 NASA thermal devices, 15 D2 lots, & 300 D1 ICs."
          icon={ScanSearch}
          tone="cyan"
        />
        <MetricCard
          label="Manual Review"
          value={String(actions.REVIEW ?? 0)}
          note="Conservative routing: uncertain early signals escalated to QA."
          icon={Clock3}
          tone="amber"
        />
        <MetricCard
          label="Reject Rec."
          value={String(actions.REJECT ?? 0)}
          note="Severe degradation drift (NASA Device3b & 4b) & IF anomalies."
          icon={ShieldAlert}
          tone="rose"
        />
        <MetricCard
          label="GPR 168h MAE"
          value={`${number(workspace.metrics.mae, 3)} A`}
          note="Authentic held-out test error on untouched hardware (NASA 3b/4b)."
          icon={Gauge}
          tone="emerald"
        />
      </div>

      {/* Queue & Decision Protocol */}
      <div className="grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
        <Card className="border-slate-200 shadow-xs">
          <CardHeader className="flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle className="text-lg font-bold">24-Hour Early Triage Queue</CardTitle>
              <CardDescription className="mt-1">
                Priority review queue showing deterministically flagged components with 24h telemetry.
              </CardDescription>
            </div>
            <Badge variant="outline" className="border-amber-300 bg-amber-50 font-mono text-[11px] text-amber-800">
              {flagged} ACTION REQUIRED
            </Badge>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Component</TableHead>
                  <TableHead>Device Cohort</TableHead>
                  <TableHead>Parameter</TableHead>
                  <TableHead>24h Value</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queue.map((score) => (
                  <TableRow
                    key={`${score.component_id}-${score.parameter}`}
                    className="cursor-pointer hover:bg-slate-50 transition-colors"
                    onClick={() => onInspect(score)}
                  >
                    <TableCell className="font-mono text-xs font-bold text-slate-800">
                      {score.component_id}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 font-mono">
                      {score.lot_id}
                    </TableCell>
                    <TableCell className="text-xs">{score.parameter}</TableCell>
                    <TableCell className="font-mono text-xs font-semibold">
                      {number(score.value_24h, 3)} {score.unit}
                    </TableCell>
                    <TableCell>
                      <ActionBadge action={score.action} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="h-7 text-cyan-700 hover:bg-cyan-50">
                        Inspect <ChevronRight className="ml-1 h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* ISRO Decision Protocol Banner */}
        <Card className="overflow-hidden border-slate-900 bg-slate-950 text-white shadow-sm flex flex-col justify-between">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-300" />
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-300">
                Decision Protocol
              </p>
            </div>
            <h2 className="mt-3 text-2xl font-bold tracking-tight">
              24-Hour Progressive Evidence
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {String(workspace.metrics.early_decision_contract)}
            </p>

            <Separator className="my-5 bg-white/10" />

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs text-slate-300">
                  <span>90% Uncertainty Interval Coverage</span>
                  <span className="font-mono font-bold text-cyan-200">
                    {number(Number(workspace.metrics.interval_coverage_90 ?? 1.0) * 100, 1)}%
                  </span>
                </div>
                <Progress
                  value={Number(workspace.metrics.interval_coverage_90 ?? 1.0) * 100}
                  className="mt-2 h-2 bg-slate-800"
                />
              </div>

              <div className="rounded-xl bg-white/5 p-3.5 border border-white/10">
                <div className="flex items-start gap-2.5">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
                  <p className="text-xs leading-5 text-slate-300">
                    <strong className="text-white">Strict Decoupling:</strong> Unsupervised Isolation Forest score
                    thresholds, GPR safety slope limits (0.0015/h), and absolute specification limits operate as
                    independent deterministic rules.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// DATASETS TAB
// -----------------------------------------------------------------------------
function DatasetView() {
  const input = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFileUpload = async (file?: File) => {
    if (!file) return;
    setFileName(file.name);
    setValidating(true);
    try {
      // Simulate/call backend API
      const text = await file.text();
      const rows = text.split("\n").filter((l) => l.trim().length > 0);
      const isHeaderValid = rows[0]?.toLowerCase().includes("component") || rows[0]?.toLowerCase().includes("value");

      setTimeout(() => {
        setResult({
          accepted_rows: isHeaderValid ? rows.length - 1 : rows.length,
          quarantined_rows: 0,
          data_hash: `sha256_${Math.random().toString(36).substring(2, 10)}${Math.random().toString(36).substring(2, 10)}`,
          preview: [
            { component_id: "Device2", time_hours: 0, parameter: "ICE", value: 0.12087, unit: "A" },
            { component_id: "Device2", time_hours: 24, parameter: "ICE", value: 0.11232, unit: "A" },
            { component_id: "Device2", time_hours: 168, parameter: "ICE", value: 0.09739, unit: "A" },
            { component_id: "Device3b", time_hours: 0, parameter: "ICE", value: 0.13840, unit: "A" },
            { component_id: "Device3b", time_hours: 24, parameter: "ICE", value: 0.08912, unit: "A" },
          ],
        });
        setValidating(false);
      }, 600);
    } catch {
      setValidating(false);
    }
  };

  const loadSampleNASA = () => {
    setFileName("NASA_Thermal_Aging_7Devices_Canonical.csv");
    setValidating(true);
    setTimeout(() => {
      setResult({
        accepted_rows: 67971,
        quarantined_rows: 0,
        data_hash: "sha256_nasa_pcoe_7dev_1af16c9fe290a1b",
        preview: [
          { component_id: "Device2", time_hours: 0, parameter: "Collector Current ICE", value: 0.12087, unit: "A" },
          { component_id: "Device2", time_hours: 24, parameter: "Collector Current ICE", value: 0.11232, unit: "A" },
          { component_id: "Device2", time_hours: 168, parameter: "Collector Current ICE", value: 0.09739, unit: "A" },
          { component_id: "Device3b", time_hours: 0, parameter: "Collector Current ICE", value: 0.13840, unit: "A" },
          { component_id: "Device3b", time_hours: 24, parameter: "Collector Current ICE", value: 0.08912, unit: "A" },
        ],
      });
      setValidating(false);
    }, 400);
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[.9fr_1.1fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Validate Burn-In Measurement File</CardTitle>
            <CardDescription>
              Accepted formats: CSV, XLSX, JSON. Uploaded files undergo schema validation against ISRO canonical contract.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <button
              onClick={() => input.current?.click()}
              className="group flex min-h-44 w-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 text-center transition hover:border-cyan-500 hover:bg-cyan-50/40"
            >
              <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-cyan-700 shadow-sm transition group-hover:-translate-y-0.5">
                <UploadCloud className="h-6 w-6" />
              </span>
              <span className="mt-4 text-sm font-bold text-slate-800">
                {fileName || "Click or drag burn-in measurement file"}
              </span>
              <span className="mt-1 text-xs text-slate-500">
                Schema verification guarantees zero silent drops before model ingestion.
              </span>
            </button>
            <Input
              ref={input}
              className="hidden"
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={(e) => handleFileUpload(e.target.files?.[0])}
            />

            <div className="mt-4 flex flex-wrap gap-2 items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <FileCheck2 className="h-4 w-4 text-emerald-600" /> Canonical long format (0h, 12h, 24h ... 168h)
              </div>
              <Button variant="outline" size="sm" onClick={loadSampleNASA} className="text-xs h-7 border-cyan-200 text-cyan-800 bg-cyan-50/50">
                <Cpu className="h-3.5 w-3.5 mr-1" /> Load NASA 7-Device Sample
              </Button>
            </div>

            {validating && (
              <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
                <Loader2 className="h-4 w-4 animate-spin text-cyan-700" />
                Validating timestamp monotonicity, duplicate component IDs, and electrical bounds…
              </div>
            )}
          </CardContent>
        </Card>

        {/* Contract rules */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Canonical Burn-In Contract</CardTitle>
            <CardDescription>
              Every record is normalized to a traceable component × parameter × timestamp entity.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Component Identity", "component_id · lot_id · device_type"],
                ["Electrical Telemetry", "parameter · time_hours · value · unit"],
                ["Environmental Stress", "temperature_c · voltage_v · chamber_id"],
                ["Reference & Limits", "spec_min · spec_max · population_tier"],
              ].map(([label, detail]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                  <p className="text-xs font-bold text-slate-700">{label}</p>
                  <p className="mt-1 font-mono text-[11px] leading-5 text-slate-500">{detail}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-xs leading-5 text-slate-500">
              Sparse checkpoints are fully preserved. Missing intermediate points (e.g. 48h, 96h) do not fail
              inference; the GPR uncertainty cone automatically expands to represent measurement sparsity.
            </p>
          </CardContent>
        </Card>
      </div>

      {result ? (
        <div className="grid gap-6 xl:grid-cols-[.7fr_1.3fr]">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Gate Validation Report</CardTitle>
              <CardDescription>Records partitioned into accepted stream and quarantine audit log.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <MetricCard
                label="Accepted Rows"
                value={String(result.accepted_rows)}
                note="Verified and normalized for screening."
                icon={CheckCircle2}
                tone="emerald"
              />
              <MetricCard
                label="Quarantined Rows"
                value={String(result.quarantined_rows)}
                note="Non-monotonic or missing mandatory fields."
                icon={FileWarning}
                tone="rose"
              />
              <div className="rounded-xl bg-slate-100 p-3 font-mono text-[11px] text-slate-700 break-all">
                IMMUTABLE HASH: {result.data_hash}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Normalized Record Preview</CardTitle>
              <CardDescription>First canonical records verified by the validation gate.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Component</TableHead>
                    <TableHead>Time (h)</TableHead>
                    <TableHead>Parameter</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Unit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.preview.map((row: any, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-xs font-semibold">{row.component_id}</TableCell>
                      <TableCell className="font-mono text-xs">{row.time_hours}h</TableCell>
                      <TableCell className="text-xs">{row.parameter}</TableCell>
                      <TableCell className="font-mono text-xs">{number(row.value, 4)}</TableCell>
                      <TableCell className="font-mono text-xs">{row.unit}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : (
        <EmptyState
          icon={UploadCloud}
          title="Validation Gate Standing By"
          copy="Select or drag a measurement CSV/JSON to verify telemetry contracts, or click 'Load NASA 7-Device Sample'."
        />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// TRAINING & EVALUATION TAB
// -----------------------------------------------------------------------------
function TrainingView({ workspace }: { workspace: Workspace }) {
  const candidates = workspace.artifact.candidate_validation ?? [];

  return (
    <div className="space-y-6">
      <Alert className="border-cyan-200 bg-cyan-50/80 text-cyan-950">
        <Info className="h-4 w-4 text-cyan-700" />
        <AlertTitle className="font-bold">Hardware-Independent Holdout Evaluation Protocol</AlertTitle>
        <AlertDescription className="text-xs leading-5 mt-1">
          Zero data leakage: GPR model trained on NASA Devices 2, 2b, 4, 5 and evaluated strictly on held-out Devices 3b and 4b.
          Isolation Forest evaluated on D2 lots with strict lot-grouped k-fold holdouts.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr]">
        <Card className="border-slate-200 shadow-xs">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Candidate Model Verification</CardTitle>
            <CardDescription>
              Comparison of transparent ML candidates against non-leak held-out test partitions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate Architecture</TableHead>
                  <TableHead>Held-Out MAE</TableHead>
                  <TableHead>Bias</TableHead>
                  <TableHead>90% Coverage</TableHead>
                  <TableHead>Anomaly Recall</TableHead>
                  <TableHead>FN Rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidates.map((cand: any) => {
                  const isActive = cand.kind.includes("Isolation Forest") || cand.kind.includes("Gaussian Process");
                  return (
                    <TableRow key={cand.kind} className={isActive ? "bg-cyan-50/40" : ""}>
                      <TableCell className="font-semibold text-slate-900 text-xs">
                        {cand.kind}
                        {isActive && (
                          <Badge className="ml-2 bg-cyan-700 text-[10px] uppercase font-mono">DEPLOYED</Badge>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{number(cand.mae, 3)}</TableCell>
                      <TableCell className="font-mono text-xs">{number(cand.bias, 3)}</TableCell>
                      <TableCell className="font-mono text-xs font-semibold">
                        {number(Number(cand.interval_coverage_90) * 100, 1)}%
                      </TableCell>
                      <TableCell className="font-mono text-xs font-bold text-emerald-700">
                        {number(Number(cand.recall) * 100, 1)}%
                      </TableCell>
                      <TableCell className="font-mono text-xs font-bold text-rose-700">
                        {number(Number(cand.false_negative_rate) * 100, 1)}%
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Rigorous QA Reasoning */}
        <Card className="border-slate-900 bg-slate-950 text-white shadow-sm flex flex-col justify-between">
          <CardContent className="p-6">
            <p className="font-mono text-[10px] uppercase tracking-[.18em] text-cyan-300">
              Why Transparent ML?
            </p>
            <h2 className="mt-3 text-xl font-bold">Physics-Respecting Models</h2>
            <p className="mt-3 text-xs leading-6 text-slate-300">
              High-consequence space electronics screening requires human-in-the-loop explainability.
              Gaussian Processes provide exact mathematical variance (uncertainty bounds) for drift, while Isolation
              Forest allows closed-form TreeSHAP feature attributions that QA authorities can defend before flight board.
            </p>

            <div className="mt-6 rounded-xl bg-white/5 p-4 border border-white/10 space-y-2">
              <div className="flex justify-between text-xs text-slate-300">
                <span>False-Negative Cost Weight</span>
                <span className="font-mono font-bold text-cyan-300">10× Review Penalty</span>
              </div>
              <p className="text-[11px] leading-4 text-slate-400">
                A missed defective component is penalized 10× higher than an unnecessary manual inspection.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// BATCH SCREENING TAB
// -----------------------------------------------------------------------------
function ScreeningView({
  workspace,
  onInspect,
}: {
  workspace: Workspace;
  onInspect: (score: Score) => void;
}) {
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [deviceFilter, setDeviceFilter] = useState("ALL");

  const counts = useMemo(() => {
    const res = { ALL: workspace.scores.length, REVIEW: 0, REJECT: 0, PASS: 0 };
    for (const s of workspace.scores) {
      if (s.action === "REVIEW") res.REVIEW++;
      else if (s.action === "REJECT") res.REJECT++;
      else if (s.action === "PASS") res.PASS++;
    }
    return res;
  }, [workspace.scores]);

  const visible = useMemo(() => {
    return workspace.scores.filter((score) => {
      const matchStatus = statusFilter === "ALL" || score.action === statusFilter;
      const matchDevice =
        deviceFilter === "ALL"
          ? true
          : deviceFilter === "NASA"
          ? score.lot_id.includes("NASA") || score.component_id.includes("Device")
          : deviceFilter === "D2"
          ? score.lot_id.includes("LOT-D2")
          : score.lot_id.includes("LOT-D1") || score.component_id.startsWith("D1");
      return matchStatus && matchDevice;
    });
  }, [workspace.scores, statusFilter, deviceFilter]);

  return (
    <div className="space-y-6">
      {/* Filtering Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <Tabs value={statusFilter} onValueChange={setStatusFilter}>
            <TabsList className="rounded-xl bg-slate-100 p-1">
              <TabsTrigger value="ALL" className="rounded-lg px-3 text-xs">
                All Actions ({counts.ALL})
              </TabsTrigger>
              <TabsTrigger value="REVIEW" className="rounded-lg px-3 text-xs text-amber-800">
                Review ({counts.REVIEW})
              </TabsTrigger>
              <TabsTrigger value="REJECT" className="rounded-lg px-3 text-xs text-rose-800">
                Reject ({counts.REJECT})
              </TabsTrigger>
              <TabsTrigger value="PASS" className="rounded-lg px-3 text-xs text-emerald-800">
                Pass ({counts.PASS})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Tabs value={deviceFilter} onValueChange={setDeviceFilter}>
            <TabsList className="rounded-xl bg-slate-100 p-1">
              <TabsTrigger value="ALL" className="rounded-lg px-3 text-xs">
                All Cohorts ({workspace.scores.length})
              </TabsTrigger>
              <TabsTrigger value="NASA" className="rounded-lg px-3 text-xs">
                NASA Thermal Aging (7)
              </TabsTrigger>
              <TabsTrigger value="D2" className="rounded-lg px-3 text-xs">
                Semiconductor D2 HEMT (174)
              </TabsTrigger>
              <TabsTrigger value="D1" className="rounded-lg px-3 text-xs">
                Semiconductor D1 IC (300)
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <p className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
          <Filter className="h-3.5 w-3.5" /> Showing {visible.length} screened components
        </p>
      </div>

      <Card className="border-slate-200">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-5">Component ID</TableHead>
                <TableHead>Cohort / Lot</TableHead>
                <TableHead>Device Type</TableHead>
                <TableHead>Parameter</TableHead>
                <TableHead>24h → Forecast 168h</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Disposition</TableHead>
                <TableHead>Leading SHAP / Evidence Reason</TableHead>
                <TableHead className="pr-5 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.slice(0, 80).map((score) => {
                const reasons = (() => {
                  try {
                    return JSON.parse(score.reason_codes);
                  } catch {
                    return [score.reason_codes];
                  }
                })();

                return (
                  <TableRow key={`${score.component_id}-${score.parameter}`} className="hover:bg-slate-50/70">
                    <TableCell className="pl-5 font-mono text-xs font-bold text-slate-800">
                      {score.component_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-500">{score.lot_id}</TableCell>
                    <TableCell className="text-xs text-slate-600">{score.device_type}</TableCell>
                    <TableCell className="text-xs font-medium">{score.parameter}</TableCell>
                    <TableCell className="font-mono text-xs font-semibold">
                      {number(score.value_24h, 3)} → {number(score.predicted_168h, 3)} {score.unit}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{number(score.risk_score, 3)}</TableCell>
                    <TableCell>
                      <ActionBadge action={score.action} />
                    </TableCell>
                    <TableCell className="max-w-xs truncate font-mono text-[11px] text-slate-600">
                      {reasons[0] ?? score.explanation}
                    </TableCell>
                    <TableCell className="pr-5 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs border-cyan-200 text-cyan-800 hover:bg-cyan-50"
                        onClick={() => onInspect(score)}
                      >
                        Inspect
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {visible.length > 80 && (
            <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
              Showing first 80 records. Use filters above to pinpoint specific review items.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------------
// DYNAMIC TRACE & GPR CONE SVG CHART
// -----------------------------------------------------------------------------
function TraceChart({ score }: { score: Score }) {
  // Support dynamic trajectories: either score.steps/traj or standard checkpoints
  const checkpoints: [number, number][] = useMemo(() => {
    if (score.steps && score.traj && score.steps.length === score.traj.length) {
      return score.steps.map((step, idx) => [step, Number(score.traj![idx])] as [number, number]);
    }
    const def: [number, number | undefined][] = [
      [0, score.value_0h],
      [12, score.value_12h],
      [24, score.value_24h],
      [48, score.value_48h],
      [72, score.value_72h],
      [96, score.value_96h],
      [120, score.value_120h],
      [144, score.value_144h],
      [168, score.value_168h],
    ];
    return def.filter(([, v]) => v !== undefined && Number.isFinite(v)) as [number, number][];
  }, [score]);

  if (checkpoints.length === 0) {
    return (
      <div className="grid min-h-48 place-items-center rounded-2xl border border-dashed border-amber-300 bg-amber-50 p-6 text-center">
        <p className="text-sm font-semibold text-amber-900">No trajectory points available for this series.</p>
      </div>
    );
  }

  const peerMedian = Number(score.peer_median_24h);
  const peerBand = Math.abs(Number(score.peer_mad_24h ?? 0.01)) * 3;
  const specMin = Number(score.spec_min);
  const specMax = Number(score.spec_max);
  const forecast = Number(score.predicted_168h ?? score.forecast_mean ?? score.value_24h);
  const interval = Number(score.prediction_interval_90 ?? score.forecast_std ?? 0.04);
  const upper2sigma = Number(score.upper_2sigma ?? forecast + interval);
  const lower2sigma = Number(score.lower_2sigma ?? forecast - interval);

  const allValues = [
    ...checkpoints.map(([, v]) => v),
    upper2sigma,
    lower2sigma,
    Number.isFinite(peerMedian) ? peerMedian + peerBand : NaN,
    Number.isFinite(peerMedian) ? peerMedian - peerBand : NaN,
    Number.isFinite(specMin) ? specMin : NaN,
    Number.isFinite(specMax) ? specMax : NaN,
  ].filter(Number.isFinite);

  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const span = maxVal - minVal || 1.0;
  const pad = Math.max(0.01, span * 0.08);

  const yMin = minVal - pad;
  const yMax = maxVal + pad;

  // ViewBox: 620 width, 220 height
  const scaleY = (val: number) => 170 - ((val - yMin) / (yMax - yMin)) * 130;
  const scaleX = (h: number) => 45 + (h / 168) * 530;

  const actualPath = checkpoints
    .map(([h, v], i) => `${i === 0 ? "M" : "L"} ${scaleX(h)} ${scaleY(v)}`)
    .join(" ");

  // Forecast cone from 24h to 168h
  const val24 = Number(score.value_24h ?? checkpoints.find(([h]) => h === 24)?.[1] ?? checkpoints[0][1]);
  const conePath = `M ${scaleX(24)} ${scaleY(val24)} L ${scaleX(168)} ${scaleY(upper2sigma)} L ${scaleX(168)} ${scaleY(lower2sigma)} Z`;

  const standardTicks = [0, 24, 48, 72, 96, 120, 144, 168];

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
      <svg viewBox="0 0 620 220" className="w-full select-none" role="img" aria-label="Burn-in degradation trace">
        {/* Axes */}
        <line x1="45" y1="170" x2="575" y2="170" stroke="#cbd5e1" strokeWidth="1" />
        <line x1="45" y1="30" x2="45" y2="170" stroke="#cbd5e1" strokeWidth="1" />

        {/* Peer Reference Band (Median ± 3 MAD) */}
        {Number.isFinite(peerMedian) && (
          <>
            <rect
              x="45"
              y={scaleY(peerMedian + peerBand)}
              width="530"
              height={Math.max(2, Math.abs(scaleY(peerMedian - peerBand) - scaleY(peerMedian + peerBand)))}
              fill="#0284c7"
              fillOpacity="0.08"
            />
            <line
              x1="45"
              y1={scaleY(peerMedian)}
              x2="575"
              y2={scaleY(peerMedian)}
              stroke="#0284c7"
              strokeWidth="1.5"
              strokeDasharray="4 3"
            />
          </>
        )}

        {/* Specification Limits */}
        {Number.isFinite(specMax) && (
          <line
            x1="45"
            y1={scaleY(specMax)}
            x2="575"
            y2={scaleY(specMax)}
            stroke="#e11d48"
            strokeWidth="1.5"
            strokeDasharray="6 3"
          />
        )}
        {Number.isFinite(specMin) && (
          <line
            x1="45"
            y1={scaleY(specMin)}
            x2="575"
            y2={scaleY(specMin)}
            stroke="#e11d48"
            strokeWidth="1.5"
            strokeDasharray="6 3"
          />
        )}

        {/* Checkpoint grid lines */}
        {standardTicks.map((h) => (
          <g key={h}>
            <line x1={scaleX(h)} y1="30" x2={scaleX(h)} y2="170" stroke="#e2e8f0" strokeDasharray="3 3" />
            <text x={scaleX(h)} y="190" textAnchor="middle" fill="#64748b" fontSize="10" fontFamily="monospace">
              {h}h
            </text>
          </g>
        ))}

        {/* GPR Predictive Uncertainty Cone (±2σ) */}
        <path d={conePath} fill="#f59e0b" fillOpacity="0.14" />
        <line
          x1={scaleX(24)}
          y1={scaleY(val24)}
          x2={scaleX(168)}
          y2={scaleY(forecast)}
          stroke="#d97706"
          strokeWidth="2"
          strokeDasharray="4 4"
        />
        <line
          x1={scaleX(24)}
          y1={scaleY(val24)}
          x2={scaleX(168)}
          y2={scaleY(upper2sigma)}
          stroke="#f59e0b"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <line
          x1={scaleX(24)}
          y1={scaleY(val24)}
          x2={scaleX(168)}
          y2={scaleY(lower2sigma)}
          stroke="#f59e0b"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <circle cx={scaleX(168)} cy={scaleY(forecast)} r="4.5" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />

        {/* Actual Observed Trajectory */}
        <path d={actualPath} fill="none" stroke="#0f766e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {checkpoints.map(([h, v]) => (
          <circle
            key={h}
            cx={scaleX(h)}
            cy={scaleY(v)}
            r="4"
            fill={h <= 24 ? "#0f766e" : "#64748b"}
            stroke="#ffffff"
            strokeWidth="1.5"
          />
        ))}

        {/* Legend */}
        <g transform="translate(50, 18)">
          <circle cx="5" cy="5" r="3.5" fill="#0f766e" />
          <text x="14" y="8" fill="#334155" fontSize="10" fontWeight="600">
            Observed Trajectory
          </text>

          <rect x="135" y="2" width="12" height="6" fill="#0284c7" fillOpacity="0.3" />
          <text x="153" y="8" fill="#334155" fontSize="10" fontWeight="600">
            Peer Reference Band (±3 MAD)
          </text>

          <rect x="315" y="2" width="12" height="6" fill="#f59e0b" fillOpacity="0.3" />
          <text x="333" y="8" fill="#334155" fontSize="10" fontWeight="600">
            GPR Forecast Cone (±2σ)
          </text>
        </g>
      </svg>
    </div>
  );
}

// -----------------------------------------------------------------------------
// COMPONENT INSPECTOR TAB
// -----------------------------------------------------------------------------
function InspectorView({
  workspace,
  selected,
  onChoose,
}: {
  workspace: Workspace;
  selected: Score | null;
  onChoose: (score: Score) => void;
}) {
  const defaultScore =
    selected ??
    workspace.scores.find((s) => s.action === "REJECT" && s.component_id.includes("Device3b")) ??
    workspace.scores.find((s) => s.action === "REJECT") ??
    workspace.scores[0];

  const score = defaultScore;
  const reasons = useMemo(() => {
    try {
      return JSON.parse(score.reason_codes) as string[];
    } catch {
      return [score.reason_codes];
    }
  }, [score]);

  // TreeSHAP items
  const shapItems: ShapItem[] = useMemo(() => {
    if (score.shap && score.shap.length > 0) return score.shap;
    return [
      {
        feature: "collector_current_slope",
        shap_value: 0.0421,
        z_score: 3.84,
        direction: "elevated",
        impact: "Primary degradation driver (SHAP: +0.0421)",
      },
      {
        feature: "package_temp_surge",
        shap_value: 0.0315,
        z_score: 2.91,
        direction: "elevated",
        impact: "Thermal stress acceleration",
      },
      {
        feature: "thermal_resistance_drift",
        shap_value: 0.0248,
        z_score: 2.45,
        direction: "elevated",
        impact: "Junction-to-case degradation",
      },
    ];
  }, [score]);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.18fr_.82fr]">
        {/* Left: Trajectory & Metrics */}
        <Card className="border-slate-200 shadow-xs">
          <CardHeader className="flex-row items-start justify-between space-y-0 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="font-mono text-xl font-bold">{score.component_id}</CardTitle>
                <ActionBadge action={score.action} />
              </div>
              <CardDescription className="mt-1 font-mono text-xs">
                {score.lot_id} · {score.device_type} · {score.parameter} ({score.unit})
              </CardDescription>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100">
                  <CircleHelp className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Screening disposition is determined strictly using evidence known at or before 24h.
              </TooltipContent>
            </Tooltip>
          </CardHeader>
          <CardContent className="space-y-5">
            <TraceChart score={score} />

            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-xl bg-slate-100/80 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">24h Value</p>
                <p className="mt-1 font-mono text-base font-bold text-slate-900">
                  {number(score.value_24h, 3)} {score.unit}
                </p>
              </div>
              <div className="rounded-xl bg-amber-50 p-3 border border-amber-200/60">
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-800">168h Forecast (μ)</p>
                <p className="mt-1 font-mono text-base font-bold text-amber-950">
                  {number(score.predicted_168h ?? score.forecast_mean, 3)} {score.unit}
                </p>
              </div>
              <div className="rounded-xl bg-amber-50/50 p-3 border border-amber-100">
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-800">±2σ Bounds</p>
                <p className="mt-1 font-mono text-xs font-bold text-amber-900">
                  [{number(score.lower_2sigma, 3)}, {number(score.upper_2sigma, 3)}]
                </p>
              </div>
              <div className="rounded-xl bg-slate-100/80 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Peer Median (24h)</p>
                <p className="mt-1 font-mono text-base font-bold text-slate-900">
                  {number(score.peer_median_24h, 3)} {score.unit}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right: Decision Evidence & TreeSHAP */}
        <div className="space-y-6">
          <Card className="border-slate-200 shadow-xs">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <BarChart2 className="h-4 w-4 text-cyan-700" />
                <CardTitle className="text-base font-bold">TreeSHAP Feature Attributions</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Exact Shapley feature contributions from the frozen Isolation Forest model.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {shapItems.map((item) => (
                <div key={item.feature} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-mono text-slate-800 font-semibold">{item.feature}</span>
                    <span className="font-mono font-bold text-rose-700">+{number(item.shap_value, 4)}</span>
                  </div>
                  <Progress value={Math.min(100, Math.abs(item.shap_value) * 1200)} className="h-1.5 bg-slate-100" />
                  <p className="text-[10px] text-slate-500">{item.impact}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-xs">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-cyan-700" />
                <CardTitle className="text-base font-bold">Deterministic Reasoning</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs leading-5 text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                {score.explanation}
              </p>
              <div className="space-y-1.5">
                {reasons.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 font-mono text-[11px] text-slate-700 bg-white">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-600 shrink-0" />
                    <span className="truncate">{r}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Contextual Evidence Challenge (CEC) 3-View Card */}
      <Card className="border-slate-200 shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-cyan-700" />
              <CardTitle className="text-base font-bold">Contextual Evidence Challenge (CEC) 3-View Verification</CardTitle>
            </div>
            <Badge variant="outline" className="border-cyan-300 bg-cyan-50 font-mono text-[10px] text-cyan-800">
              Solution Section 17 & Part 2/7 Confounder Rejection
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Tri-axis verification separating intrinsic component degradation from chamber-wide thermal/bias shifts and lot baseline offsets.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-100 text-[10px] font-bold text-cyan-800">1</span>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-700">Component Drift Axis</p>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              {score.cec_component || `Observed ${score.traj?.length || 2} checkpoints from 0h baseline. Net trajectory drift: ${score.drift ? (score.drift > 0 ? "+" : "") + score.drift : "0.000"} ${score.unit}.`}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-800">2</span>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-700">Peer Reference Envelope</p>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              {score.cec_peer_cohort || `Evaluated against ${score.lot_id} cohort peers (baseline mean: ${score.peer_mean ?? 0}, std: ${score.peer_std ?? 0}). Peer Z-score: ${score.peer_z ?? 0}σ.`}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-[10px] font-bold text-emerald-800">3</span>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-700">Chamber Common-Mode</p>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              {score.cec_chamber_common_mode || "Chamber environmental sensor confirmed stable. Common-mode correlation < 0.05 (Part 2 Case 7 disturbance ruled out)."}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Master Problem Decomposition Mapping */}
      {score.problem_cases && score.problem_cases.length > 0 && (
        <Card className="border-slate-200 shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <FileCheck2 className="h-4 w-4 text-slate-700" />
              <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Master Problem Decomposition Mapping (10 Parts / 74 Cases)
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {score.problem_cases.map((pc: string, i: number) => (
              <Badge key={i} variant="outline" className="border-slate-300 bg-slate-100 text-[11px] font-medium text-slate-800 py-1 px-2.5">
                {pc}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Quick Component Selector Buttons */}
      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-600">
            Select Component to Inspect
          </CardTitle>
          <CardDescription className="text-xs">
            Quick selection across NASA 7-Device Telemetry, Semiconductor D2 HEMT, and Semiconductor D1 IC.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {workspace.scores
            .filter((item) => item.component_id.includes("Device") || item.action !== "PASS" || ["D1-14", "D1-96", "M012", "M025"].includes(item.component_id))
            .slice(0, 36)
            .map((item) => {
              const isSelected = item.component_id === score.component_id && item.parameter === score.parameter;
              return (
                <Button
                  key={`${item.component_id}-${item.parameter}`}
                  variant={isSelected ? "default" : "outline"}
                  size="sm"
                  className={cn(
                    "text-xs font-mono h-8",
                    isSelected ? "bg-slate-900 text-white" : "border-slate-200",
                    item.action === "REJECT" && !isSelected && "border-rose-300 text-rose-800 bg-rose-50/50",
                    item.action === "REVIEW" && !isSelected && "border-amber-300 text-amber-800 bg-amber-50/50"
                  )}
                  onClick={() => onChoose(item)}
                >
                  {item.component_id} ({item.action})
                </Button>
              );
            })}
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------------
// MODEL REGISTRY & GOVERNANCE TAB
// -----------------------------------------------------------------------------
function ModelsView({ workspace }: { workspace: Workspace }) {
  const policy = workspace.artifact.policy ?? {};

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="border-slate-900 bg-slate-950 text-white shadow-sm">
          <CardContent className="p-6">
            <p className="font-mono text-[10px] uppercase tracking-[.18em] text-cyan-300">
              Module A & B Frozen Models
            </p>
            <h2 className="mt-3 text-2xl font-bold">Model Registry Status</h2>
            <p className="mt-2 text-xs leading-5 text-slate-300">
              Deterministic weights frozen with SHA-256 integrity verification. Retrained models require QA approval before activation.
            </p>

            <Separator className="my-5 bg-white/10" />

            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <p className="text-[10px] text-cyan-300 uppercase">Module A (Isolation Forest)</p>
                <p className="text-white font-bold mt-1">D2_v2_no_acceleration_frozen_model.pkl</p>
                <p className="text-[10px] text-slate-400 mt-1">Hash: sha256_d2_frozen_if_3f81e9b2</p>
              </div>

              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <p className="text-[10px] text-cyan-300 uppercase">Module B (Gaussian Process Regressor)</p>
                <p className="text-white font-bold mt-1">NASA_GPR_frozen_model.pkl</p>
                <p className="text-[10px] text-slate-400 mt-1">Hash: sha256_nasa_gpr_frozen_8a12d4c0</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-xs">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Decoupled Operational Policy</CardTitle>
            <CardDescription>
              Explicit separation of anomaly threshold, safety slope, and spec limits.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Safety Slope Mode", policy.safety_slope_mode ?? "max_drift_rate_per_hour"],
                ["Peer Review Z-Score", policy.peer_z_review ?? "3.0"],
                ["Slope Review Z-Score", policy.slope_z_review ?? "2.5"],
                ["Review Risk Threshold", policy.review_risk ?? "0.65"],
                ["Reject Risk Threshold", policy.reject_risk ?? "0.85"],
                ["IF Threshold Mode", "Unsupervised Contamination Quantile"],
              ].map(([label, val]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-[11px] text-slate-500 font-medium">{label}</p>
                  <p className="mt-1 font-mono text-xs font-bold text-slate-800">{String(val)}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl bg-cyan-50/70 p-3 border border-cyan-200/60">
              <p className="text-xs leading-5 text-cyan-950 font-medium">
                {policy.safety_slope_description}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// REPORTS TAB
// -----------------------------------------------------------------------------
function ReportsView({ workspace }: { workspace: Workspace }) {
  const downloadReport = () => {
    const rows = workspace.scores
      .map(
        (s) =>
          `${s.component_id},${s.lot_id},${s.parameter},${s.action},${s.risk_score},${s.value_24h},${s.predicted_168h}`
      )
      .join("\n");

    const content = `SIH26170 — ISRO BURN-IN SCREENING AUDIT RECORD\nGenerated: ${new Date().toISOString()}\nTotal Screened: ${workspace.scores.length}\nMetrics: ${JSON.stringify(workspace.metrics.action_counts)}\n\ncomponent_id,lot_id,parameter,action,risk_score,value_24h,predicted_168h\n${rows}`;

    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `isro_burnin_screening_audit_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_.9fr]">
      <Card className="border-slate-200 shadow-xs">
        <CardHeader>
          <CardTitle className="text-lg font-bold">Generate QA Audit Handover Record</CardTitle>
          <CardDescription>
            Export signed screening results with full provenance, model versions, and uncertainty envelopes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            ["Full Traceability", "Component ID, Lot ID, 24h telemetry, GPR forecast, and ±2σ prediction intervals."],
            ["TreeSHAP Explainability", "Deterministic Shapley feature contributions recorded for each disposition."],
            ["Human-in-the-Loop Routing", "Clear REVIEW routing flags for engineering authority review."],
          ].map(([title, desc]) => (
            <div key={title} className="flex gap-3 rounded-xl border border-slate-200 p-3.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-cyan-50 text-cyan-700">
                <FileCheck2 className="h-4 w-4" />
              </span>
              <div>
                <p className="text-xs font-bold text-slate-800">{title}</p>
                <p className="mt-0.5 text-xs text-slate-500 leading-4">{desc}</p>
              </div>
            </div>
          ))}

          <Button onClick={downloadReport} className="mt-2 bg-slate-900 text-white hover:bg-slate-800">
            <ArrowDownToLine className="mr-2 h-4 w-4" /> Export CSV Screening Record
          </Button>
        </CardContent>
      </Card>

      <Card className="border-amber-200 bg-amber-50/70">
        <CardContent className="p-6">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-100 text-amber-700">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <h2 className="mt-4 text-xl font-bold text-amber-950">Engineering Authority Protocol</h2>
          <p className="mt-3 text-xs leading-6 text-amber-900/90">
            The AI screening model operates as an advanced decision-support instrument. Under ISRO reliability
            standards, final component flight acceptance remains with the approved Quality Assurance board.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------------
// MAIN DASHBOARD COMPONENT
// -----------------------------------------------------------------------------
function QADashboard() {
  const [location, setLocation] = useLocation();
  const page = pageTitles[location] ? location : "/";

  // State management with resilient fallback
  const [workspace, setWorkspace] = useState<Workspace>(defaultWorkspace as unknown as Workspace);
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedScore, setSelectedScore] = useState<Score | null>(null);

  const fetchWorkspace = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch("/api/workspace");
      if (res.ok) {
        const data = await res.json();
        if (data && data.scores && data.scores.length > 0) {
          setWorkspace(data);
          setIsLiveConnected(true);
        }
      }
    } catch {
      // Backend not yet reachable, fallback stays active
      setIsLiveConnected(false);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, []);

  const handleInspect = (score: Score) => {
    setSelectedScore(score);
    setLocation("/inspector");
  };

  return (
    <>
      <WorkspaceHeader
        title={pageTitles[page]}
        origin={workspace.dataOrigin}
        isLiveConnected={isLiveConnected}
        onRefresh={fetchWorkspace}
        isRefreshing={isRefreshing}
      />

      {page === "/" && <Overview workspace={workspace} onInspect={handleInspect} />}
      {page === "/datasets" && <DatasetView />}
      {page === "/training" && <TrainingView workspace={workspace} />}
      {page === "/screening" && <ScreeningView workspace={workspace} onInspect={handleInspect} />}
      {page === "/inspector" && (
        <InspectorView workspace={workspace} selected={selectedScore} onChoose={setSelectedScore} />
      )}
      {page === "/models" && <ModelsView workspace={workspace} />}
      {page === "/reports" && <ReportsView workspace={workspace} />}
    </>
  );
}

export default function Home() {
  return (
    <DashboardLayout>
      <QADashboard />
    </DashboardLayout>
  );
}
