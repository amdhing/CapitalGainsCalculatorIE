import { useState, useMemo } from 'react';
import {
  Card, Text, Table, Stack, Title, Group, Badge, Select, Radio,
  Pagination, Tooltip, NumberInput, Button, Grid,
} from '@mantine/core';
import { IconHelpCircle, IconRefresh, IconChevronUp, IconChevronDown, IconAlertTriangle } from '@tabler/icons-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend, ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts';
import { CalculateResponse, PriorTaxPaid } from '../api/client';

interface Props {
  data: CalculateResponse;
  onRecalculate: (priorTaxPaid: PriorTaxPaid[]) => Promise<void>;
}

const ROWS_PER_PAGE = 15;

/** Map currency codes to their symbols. */
const CURRENCY_SYMBOLS: Record<string, string> = {
  EUR: '\u20AC',
  USD: '$',
  GBP: '\u00A3',
};

function fmt(amount: number, currency: string): string {
  const sym = CURRENCY_SYMBOLS[currency] || currency;
  const sign = amount < 0 ? '-' : '';
  return `${sign}${sym}${Math.abs(amount).toFixed(2)}`;
}

/** Human-friendly display + color metadata for known broker sources. */
const SOURCE_META: Record<string, { label: string; badge: string; stroke: string }> = {
  revolut: { label: 'Revolut', badge: 'teal', stroke: '#12b886' },
  zerodha: { label: 'Zerodha', badge: 'orange', stroke: '#f76707' },
  trading212: { label: 'Trading 212', badge: 'blue', stroke: '#339af0' },
};

function sourceLabel(source: string): string {
  return SOURCE_META[source]?.label ?? (source || '-');
}

function sourceBadge(source: string): string {
  return SOURCE_META[source]?.badge ?? 'gray';
}

function sourceStroke(source: string): string {
  return SOURCE_META[source]?.stroke ?? '#868e96';
}

export default function ResultsPane({ data, onRecalculate }: Props) {
  const { tax_summary, ticker_breakdown, source_summary, total_tax_due_eur, deemed_disposal_errors } = data;

  // Map of ticker -> set of years with deemed disposal errors
  const ddErrorMap = useMemo(() => {
    const map: Record<string, Set<number>> = {};
    for (const e of deemed_disposal_errors) {
      if (!map[e.ticker]) map[e.ticker] = new Set();
      map[e.ticker].add(e.year);
    }
    return map;
  }, [deemed_disposal_errors]);

  const stockRows = tax_summary.filter((r) => r.asset_type === 'Stocks');
  const etfRows = tax_summary.filter((r) => r.asset_type === 'ETFs');
  const offshoreRows = tax_summary.filter((r) => r.asset_type === 'Offshore Funds');

  // --- Prior tax paid state ---
  // key: `${year}-${asset_type}`, value: amount in EUR
  const [priorAmounts, setPriorAmounts] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const row of tax_summary) {
      initial[`${row.year}-${row.asset_type}`] = row.already_paid_eur;
    }
    return initial;
  });

  const [recalculating, setRecalculating] = useState(false);

  const handlePriorChange = (key: string, value: number) => {
    setPriorAmounts((prev) => ({ ...prev, [key]: value }));
  };

  // --- Deemed disposal paid state (ETF rows only) ---
  const [deemedPaidAmounts, setDeemedPaidAmounts] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const row of etfRows) {
      initial[`${row.year}-ETFs`] = row.deemed_already_paid_eur;
    }
    return initial;
  });

  const handleDeemedPaidChange = (key: string, value: number) => {
    setDeemedPaidAmounts((prev) => ({ ...prev, [key]: value }));
  };

  const handleRecalculate = async () => {
    const priorTaxPaid: PriorTaxPaid[] = [];
    for (const [key, amount] of Object.entries(priorAmounts)) {
      const [yearStr, assetType] = key.split('-');
      const year = parseInt(yearStr, 10);
      if (amount > 0) {
        priorTaxPaid.push({ year, asset_type: assetType, amount_eur: amount });
      }
    }
    setRecalculating(true);
    try {
      await onRecalculate(priorTaxPaid);
    } finally {
      setRecalculating(false);
    }
  };

  // --- Per-ticker breakdown filters ---
  const years = useMemo(() => {
    const s = new Set<number>();
    ticker_breakdown.forEach((r) => s.add(r.year));
    return Array.from(s).sort((a, b) => b - a);
  }, [ticker_breakdown]);

  const tickers = useMemo(() => {
    const s = new Set<string>();
    ticker_breakdown.forEach((r) => s.add(r.ticker));
    return Array.from(s).sort();
  }, [ticker_breakdown]);

  // Per-source chart data: one series per (source, metric) across years.
  const chartSources = useMemo(
    () => Array.from(new Set(source_summary.map((s) => s.source))),
    [source_summary],
  );

  const chartData = useMemo(() => {
    const years = Array.from(new Set(source_summary.map((s) => s.year))).sort((a, b) => a - b);
    return years.map((year) => {
      const row: Record<string, string | number> = { year };
      for (const s of source_summary) {
        if (s.year !== year) continue;
        const label = sourceLabel(s.source);
        row[`${label} · Gains`] = Number(s.realized_gains_eur.toFixed(2));
        row[`${label} · Dividends`] = Number(s.dividends_eur.toFixed(2));
      }
      return row;
    });
  }, [source_summary]);

  const chartLines = useMemo(() => {
    return chartSources.flatMap((src) => {
      const label = sourceLabel(src);
      return [
        { key: `${src}-gains`, dataKey: `${label} · Gains`, name: `${label} · Gains`, stroke: sourceStroke(src) },
        { key: `${src}-div`, dataKey: `${label} · Dividends`, name: `${label} · Dividends`, stroke: sourceStroke(src), dashed: true },
      ];
    });
  }, [chartSources]);

  const [filterMode, setFilterMode] = useState<'year' | 'ticker' | 'all'>('year');
  const [selectedYear, setSelectedYear] = useState<string | null>(years.length > 0 ? String(years[0]) : null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // --- Sort state for per-ticker breakdown ---
  type SortColumn = 'gain' | 'dividends' | 'type' | 'name' | 'year' | null;
  const [sortColumn, setSortColumn] = useState<SortColumn>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const toggleSort = (col: SortColumn) => {
    if (sortColumn === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(col);
      setSortDir('desc');
    }
  };

  const filteredBreakdown = useMemo(() => {
    let rows = [...ticker_breakdown];
    if (filterMode === 'year' && selectedYear) {
      rows = rows.filter((r) => r.year === Number(selectedYear));
    } else if (filterMode === 'ticker' && selectedTicker) {
      rows = rows.filter((r) => r.ticker === selectedTicker);
    }
    // Default (no explicit sort): name ascending, then year ascending, so a
    // ticker's rows appear together in chronological order.
    if (sortColumn === null) {
      rows.sort((a, b) => {
        const nameA = a.long_name || a.ticker;
        const nameB = b.long_name || b.ticker;
        const cmp = nameA.localeCompare(nameB);
        if (cmp !== 0) return cmp;
        return a.year - b.year;
      });
    } else if (sortColumn === 'gain') {
      rows.sort((a, b) => sortDir === 'asc'
        ? a.realized_gains_eur - b.realized_gains_eur
        : b.realized_gains_eur - a.realized_gains_eur);
    } else if (sortColumn === 'dividends') {
      rows.sort((a, b) => sortDir === 'asc'
        ? a.dividends_eur - b.dividends_eur
        : b.dividends_eur - a.dividends_eur);
    } else if (sortColumn === 'type') {
      rows.sort((a, b) => {
        const cmp = a.asset_type.localeCompare(b.asset_type);
        if (cmp !== 0) return sortDir === 'asc' ? cmp : -cmp;
        return b.realized_gains_eur - a.realized_gains_eur; // secondary: gain desc
      });
    } else if (sortColumn === 'year') {
      rows.sort((a, b) => {
        const cmp = a.year - b.year;
        if (cmp !== 0) return sortDir === 'asc' ? cmp : -cmp;
        const nameA = a.long_name || a.ticker;
        const nameB = b.long_name || b.ticker;
        return nameA.localeCompare(nameB); // secondary: name asc
      });
    } else if (sortColumn === 'name') {
      rows.sort((a, b) => {
        const nameA = a.long_name || a.ticker;
        const nameB = b.long_name || b.ticker;
        const cmp = nameA.localeCompare(nameB);
        if (cmp !== 0) return sortDir === 'asc' ? cmp : -cmp;
        return sortDir === 'asc' ? a.year - b.year : b.year - a.year; // secondary: year
      });
    }
    return rows;
  }, [ticker_breakdown, filterMode, selectedYear, selectedTicker, sortColumn, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filteredBreakdown.length / ROWS_PER_PAGE));
  const paginatedRows = filteredBreakdown.slice(
    (page - 1) * ROWS_PER_PAGE,
    page * ROWS_PER_PAGE,
  );

  // Reset page when filter changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useMemo(() => setPage(1), [filterMode, selectedYear, selectedTicker, sortColumn]);

  return (
    <Stack my="lg">
      <Title order={3}>Tax Calculation Results</Title>

      <Group>
        <Badge size="xl" color="red">
          Total Tax Due: &euro;{total_tax_due_eur.toFixed(2)}
        </Badge>
      </Group>

      {source_summary.length > 0 && (
        <Card withBorder shadow="sm" p="lg">
          <Title order={4}>Per-Source Summary</Title>
          <Text size="xs" c="dimmed" mb="md">
            One line per source (broker) per year. Amounts are shown in EUR.
          </Text>
          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Year</Table.Th>
                    <Table.Th>Source</Table.Th>
                    <Table.Th>Total Gains</Table.Th>
                    <Table.Th>Total Dividends</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {source_summary.map((s, i) => (
                    <Table.Tr key={i}>
                      <Table.Td>{s.year}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" size="sm" color={sourceBadge(s.source)}>
                          {sourceLabel(s.source)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{fmt(s.realized_gains_eur, 'EUR')}</Table.Td>
                      <Table.Td>{fmt(s.dividends_eur, 'EUR')}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  {chartLines.map((l) => (
                    <Line
                      key={l.key}
                      type="monotone"
                      dataKey={l.dataKey}
                      name={l.name}
                      stroke={l.stroke}
                      strokeDasharray={l.dashed ? '4 3' : undefined}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {stockRows.length > 0 && (
        <Card withBorder shadow="sm" p="lg">
          <Title order={4}>Stock CGT Summary</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Gross</Table.Th>
                <Table.Th>Exemption</Table.Th>
                <Table.Th>Loss Used</Table.Th>
                <Table.Th>Taxable</Table.Th>
                <Table.Th>Rate</Table.Th>
                <Table.Th>Tax Due</Table.Th>
                <Table.Th>Already Paid</Table.Th>
                <Table.Th>Net Due</Table.Th>
                <Table.Th>Loss CF</Table.Th>

              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {stockRows.map((r, i) => {
                const key = `${r.year}-${r.asset_type}`;
                return (
                  <Table.Tr key={i}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>{fmt(r.realized_gains_gross_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.cgt_exemption_applied_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.carry_forward_loss_used_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.taxable_gains_net_eur, 'EUR')}</Table.Td>
                    <Table.Td>{r.tax_rate}</Table.Td>
                    <Table.Td fw={700}>{fmt(r.tax_liability_eur, 'EUR')}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        value={priorAmounts[key] ?? 0}
                        onChange={(v) => handlePriorChange(key, Number(v) || 0)}
                        min={0}
                        decimalScale={2}
                        size="xs"
                        w={110}
                        hideControls
                      />
                    </Table.Td>
                    <Table.Td fw={700} c={r.net_due_eur > 0 ? 'red' : 'green'}>
                      {fmt(r.net_due_eur, 'EUR')}
                      {r.net_due_eur < 0 && <Text span size="xs" c="dimmed" ml={4}>(refund due)</Text>}
                    </Table.Td>
                    <Table.Td>{fmt(r.losses_carried_forward_eur, 'EUR')}</Table.Td>

                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {etfRows.length > 0 && (
        <Card withBorder shadow="sm" p="lg">
          <Title order={4}>ETF Tax Summary</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Gross</Table.Th>
                <Table.Th>Taxable</Table.Th>
                <Table.Th>Deemed</Table.Th>
                <Table.Th>Deemed Pd</Table.Th>
                <Table.Th>Rate</Table.Th>
                <Table.Th>Tax Due</Table.Th>
                <Table.Th>Already Paid</Table.Th>
                <Table.Th>Net Due</Table.Th>
              </Table.Tr>

            </Table.Thead>
            <Table.Tbody>
              {etfRows.map((r, i) => {
                const key = `${r.year}-${r.asset_type}`;
                return (
                  <Table.Tr key={i}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>{fmt(r.realized_gains_gross_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.taxable_gains_net_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.deemed_disposal_eur, 'EUR')}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        value={deemedPaidAmounts[key] ?? 0}
                        onChange={(v) => handleDeemedPaidChange(key, Number(v) || 0)}
                        min={0}
                        decimalScale={2}
                        size="xs"
                        w={90}
                        hideControls
                      />
                    </Table.Td>
                    <Table.Td>{r.tax_rate}</Table.Td>
                    <Table.Td fw={700}>{fmt(r.tax_liability_eur, 'EUR')}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        value={priorAmounts[key] ?? 0}
                        onChange={(v) => handlePriorChange(key, Number(v) || 0)}
                        min={0}
                        decimalScale={2}
                        size="xs"
                        w={110}
                        hideControls
                      />
                    </Table.Td>
                    <Table.Td fw={700} c={r.net_due_eur > 0 ? 'red' : 'green'}>
                      {fmt(r.net_due_eur - (deemedPaidAmounts[key] ?? 0), 'EUR')}
                      {(r.net_due_eur - (deemedPaidAmounts[key] ?? 0)) < 0 && <Text span size="xs" c="dimmed" ml={4}>(refund due)</Text>}
                    </Table.Td>

                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {offshoreRows.length > 0 && (
        <Card withBorder shadow="sm" p="lg">
          <Title order={4}>Offshore Fund Tax Summary</Title>
          <Text size="xs" c="dimmed" mb="md">
            Non-distributing offshore funds outside the EU/EEA/OECD (e.g. Indian
            SEBI ETFs) are taxed on disposal as <strong>Case IV income</strong> at
            your marginal rate — not CGT and not the 38% equivalent-fund exit tax.
          </Text>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Gross</Table.Th>
                <Table.Th>Taxable</Table.Th>
                <Table.Th>Rate</Table.Th>
                <Table.Th>Tax Due</Table.Th>
                <Table.Th>Already Paid</Table.Th>
                <Table.Th>Net Due</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {offshoreRows.map((r, i) => {
                const key = `${r.year}-${r.asset_type}`;
                return (
                  <Table.Tr key={i}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>{fmt(r.realized_gains_gross_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.taxable_gains_net_eur, 'EUR')}</Table.Td>
                    <Table.Td>{r.tax_rate}</Table.Td>
                    <Table.Td fw={700}>{fmt(r.tax_liability_eur, 'EUR')}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        value={priorAmounts[key] ?? 0}
                        onChange={(v) => handlePriorChange(key, Number(v) || 0)}
                        min={0}
                        decimalScale={2}
                        size="xs"
                        w={110}
                        hideControls
                      />
                    </Table.Td>
                    <Table.Td fw={700} c={r.net_due_eur > 0 ? 'red' : 'green'}>
                      {fmt(r.net_due_eur, 'EUR')}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
          <Text size="xs" c="dimmed" mt="sm">
            Note: look-through income (Case III) on the underlying fund is not
            yet modelled, and USC/PRSI on this Case IV income is not added — the
            amount shown may understate your total liability.
          </Text>
        </Card>
      )}

      {/* Recalculate button */}
      {(stockRows.length > 0 || etfRows.length > 0 || offshoreRows.length > 0) && (
        <Group justify="flex-end">
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={handleRecalculate}
            loading={recalculating}
            color="blue"
          >
            {recalculating ? 'Recalculating...' : 'Recalculate with Prior Tax'}
          </Button>
        </Group>
      )}

      {ticker_breakdown.length > 0 && (
        <Card withBorder shadow="sm" p="lg">
          <Title order={4} mb="sm">Per-Ticker Breakdown</Title>

          <Radio.Group
            value={filterMode}
            onChange={(v) => {
              setFilterMode(v as typeof filterMode);
              setPage(1);
            }}
            mb="sm"
          >
            <Group>
              <Radio value="all" label="Show all" />
              <Radio value="year" label="Filter by year" />
              <Radio value="ticker" label="Filter by ticker" />
            </Group>
          </Radio.Group>

          {filterMode === 'year' && years.length > 0 && (
            <Select
              placeholder="Select a year"
              data={years.map(String)}
              value={selectedYear}
              onChange={(v) => { setSelectedYear(v); setPage(1); }}
              w={200}
              mb="sm"
              clearable
            />
          )}

          {filterMode === 'ticker' && tickers.length > 0 && (
            <Select
              placeholder="Select a ticker"
              data={tickers}
              value={selectedTicker}
              onChange={(v) => { setSelectedTicker(v); setPage(1); }}
              w={200}
              mb="sm"
              searchable
              clearable
            />
          )}

          <Text size="sm" c="dimmed" mb="xs">
            Showing {paginatedRows.length} of {filteredBreakdown.length} rows
          </Text>

          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('year')}
                >
                  <Group gap={4} wrap="nowrap">
                    Year
                    {sortColumn === 'year'
                      ? (sortDir === 'asc' ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />)
                      : null}
                  </Group>
                </Table.Th>
                <Table.Th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('name')}
                >
                  <Group gap={4} wrap="nowrap">
                    Name
                    {sortColumn === 'name'
                      ? (sortDir === 'asc' ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />)
                      : null}
                  </Group>
                </Table.Th>
                <Table.Th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('type')}
                >
                  <Group gap={4} wrap="nowrap">
                    Type
                    {sortColumn === 'type'
                      ? (sortDir === 'asc' ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />)
                      : null}
                  </Group>
                </Table.Th>
                <Table.Th>Source</Table.Th>
                <Table.Th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('gain')}
                >
                  <Group gap={4} wrap="nowrap">
                    Gain
                    {sortColumn === 'gain'
                      ? (sortDir === 'asc' ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />)
                      : null}
                  </Group>
                </Table.Th>
                <Table.Th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('dividends')}
                >
                  <Group gap={4} wrap="nowrap">
                    Div Total
                    {sortColumn === 'dividends'
                      ? (sortDir === 'asc' ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />)
                      : null}
                  </Group>
                </Table.Th>
                <Table.Th>Div IE</Table.Th>
                <Table.Th>Div Foreign</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {paginatedRows.map((r, i) => {
                const hasName = r.long_name && r.long_name.length > 0;
                return (
                  <Table.Tr key={i}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>
                      <Group gap="xs" wrap="nowrap">
                        <Text fw={600} component="span">{r.ticker}</Text>
                        {r.currency && r.currency !== 'EUR' && (
                          <Badge variant="light" size="xs">{r.currency}</Badge>
                        )}
                        {hasName ? (
                          <Tooltip label={r.long_name} multiline maw={400}>
                            <Text size="xs" c="dimmed" truncate maw={250}>
                              {r.long_name}
                            </Text>
                          </Tooltip>
                        ) : (
                          <Tooltip label="Description unavailable. We'll look into this ticker." multiline maw={300}>
                            <Group gap={4} wrap="nowrap">
                              <IconHelpCircle size={14} />
                              <Text size="xs" fs="italic" c="dimmed">unavailable</Text>
                            </Group>
                          </Tooltip>
                        )}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} wrap="nowrap">
                        <Text component="span">{r.asset_type}</Text>
                        {ddErrorMap[r.ticker]?.has(r.year) && (
                          <Tooltip label={`Deemed disposal could not be calculated — historical price unavailable`} multiline maw={300}>
                            <IconAlertTriangle size={14} color="var(--mantine-color-yellow-6)" />
                          </Tooltip>
                        )}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      {r.source ? (
                        <Badge variant="light" size="xs" color={sourceBadge(r.source)}>
                          {sourceLabel(r.source)}
                        </Badge>
                      ) : '-'}
                    </Table.Td>
                    <Table.Td>{fmt(r.realized_gains_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.dividends_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.dividends_irish_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.dividends_foreign_eur, 'EUR')}</Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>

          {pageCount > 1 && (
            <Group justify="center" mt="sm">
              <Pagination total={pageCount} value={page} onChange={setPage} />
            </Group>
          )}
        </Card>
      )}
    </Stack>
  );
}
