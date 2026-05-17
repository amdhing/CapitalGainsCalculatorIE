const API_BASE = '/api';

export interface UploadResponse {
  file_id: string;
  filename: string;
  rows: number;
  preview: Record<string, unknown>[];
}

export interface CalculateResponse {
  calculation_id: string;
  tax_summary: TaxLine[];
  ticker_breakdown: TickerBreakdown[];
  total_tax_due_eur: number;
  console_output: string;
}

export interface PriorTaxPaid {
  year: number;
  asset_type: string;
  amount_eur: number;
}

export interface TaxLine {
  year: number;
  asset_type: string;
  realized_gains_gross_eur: number;
  cgt_exemption_applied_eur: number;
  carry_forward_loss_used_eur: number;
  taxable_gains_net_eur: number;
  tax_rate: string;
  tax_liability_eur: number;
  already_paid_eur: number;
  net_due_eur: number;
  losses_carried_forward_eur: number;
  dividends_irish_eur: number;
  dividends_foreign_eur: number;
}

export interface TickerBreakdown {
  year: number;
  ticker: string;
  asset_type: string;
  currency: string;
  realized_gains_eur: number;
  dividends_eur: number;
  dividends_irish_eur: number;
  dividends_foreign_eur: number;
  long_name?: string;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function calculate(files: string[], marginRate = 40, priorTaxPaid: PriorTaxPaid[] = []): Promise<CalculateResponse> {
  const res = await fetch(`${API_BASE}/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files, margin_rate: marginRate, csv_export: false, prior_tax_paid: priorTaxPaid }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResult(id: string): Promise<CalculateResponse> {
  const res = await fetch(`${API_BASE}/results/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
