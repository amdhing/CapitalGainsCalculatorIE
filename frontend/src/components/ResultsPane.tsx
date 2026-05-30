import { useState, useMemo } from 'react';
import {
  Card, Text, Table, Stack, Title, Group, Badge, Select, Radio,
  Pagination, Tooltip, NumberInput, Button,
} from '@mantine/core';
import { IconHelpCircle, IconRefresh, IconChevronUp, IconChevronDown } from '@tabler/icons-react';
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

export default function ResultsPane({ data, onRecalculate }: Props) {
  const { tax_summary, ticker_breakdown, total_tax_due_eur } = data;

  const stockRows = tax_summary.filter((r) => r.asset_type === 'Stocks');
  const etfRows = tax_summary.filter((r) => r.asset_type === 'ETFs');

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

  const [filterMode, setFilterMode] = useState<'year' | 'ticker' | 'all'>('year');
  const [selectedYear, setSelectedYear] = useState<string | null>(years.length > 0 ? String(years[0]) : null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // --- Sort state for per-ticker breakdown ---
  type SortColumn = 'gain' | 'dividends' | null;
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
    // Apply sorting
    if (sortColumn === 'gain') {
      rows.sort((a, b) => sortDir === 'asc' ? a.realized_gains_eur - b.realized_gains_eur : b.realized_gains_eur - a.realized_gains_eur);
    } else if (sortColumn === 'dividends') {
      rows.sort((a, b) => sortDir === 'asc' ? a.dividends_eur - b.dividends_eur : b.dividends_eur - a.dividends_eur);
    }
    return rows;
  }, [ticker_breakdown, filterMode, selectedYear, selectedTicker, sortColumn, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filteredBreakdown.length / ROWS_PER_PAGE));
  const paginatedRows = filteredBreakdown.slice(
    (page - 1) * ROWS_PER_PAGE,
    page * ROWS_PER_PAGE,
  );

  // Reset page when filter changes
  useMemo(() => setPage(1), [filterMode, selectedYear, selectedTicker]);

  return (
    <Stack my="lg">
      <Title order={3}>Tax Calculation Results</Title>

      <Group>
        <Badge size="xl" color="red">
          Total Tax Due: &euro;{total_tax_due_eur.toFixed(2)}
        </Badge>
      </Group>

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

      {/* Recalculate button */}
      {(stockRows.length > 0 || etfRows.length > 0) && (
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
                <Table.Th>Year</Table.Th>
                <Table.Th>Ticker</Table.Th>
                <Table.Th>Type</Table.Th>
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
                const cur = r.currency || 'EUR';
                return (
                  <Table.Tr key={i}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>
                      <Group gap="xs" wrap="nowrap">
                        <Text fw={600} component="span">{r.ticker}</Text>
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
                    <Table.Td>{r.asset_type}</Table.Td>
                    <Table.Td>{fmt(r.realized_gains_eur, cur)}</Table.Td>
                    <Table.Td>{fmt(r.dividends_eur, cur)}</Table.Td>
                    <Table.Td>{fmt(r.dividends_irish_eur, 'EUR')}</Table.Td>
                    <Table.Td>{fmt(r.dividends_foreign_eur, cur)}</Table.Td>
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
