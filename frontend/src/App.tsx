import { useState, useCallback } from 'react';
import { AppShell, Group, Title, Text, Loader, Center, Stack } from '@mantine/core';
import { IconCurrencyEuro } from '@tabler/icons-react';
import UploadPane from './components/UploadPane';
import ResultsPane from './components/ResultsPane';
import { CalculateResponse, calculate, PriorTaxPaid } from './api/client';

export default function App() {
  const [results, setResults] = useState<CalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileIds, setFileIds] = useState<string[]>([]);

  // Called by UploadPane when calculation completes — stores file IDs for later re-calcs
  const handleResults = useCallback((r: CalculateResponse, fids?: string[]) => {
    setResults(r);
    if (fids) setFileIds(fids);
  }, []);

  const handleRecalculate = useCallback(async (priorTaxPaid: PriorTaxPaid[]) => {
    if (fileIds.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await calculate(fileIds, 40, priorTaxPaid);
      setResults(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Recalculation failed');
    } finally {
      setLoading(false);
    }
  }, [fileIds]);

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md">
          <IconCurrencyEuro size={28} />
          <Title order={3}>INION Irish Capital Gains Calculator</Title>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {error && (
          <Text c="red" mb="md" style={{ whiteSpace: 'pre-wrap' }}>{error}</Text>
        )}
        <UploadPane onResults={handleResults} onLoading={setLoading} onError={setError} />
        {loading && (
          <Center my="xl">
            <Stack align="center" gap="sm">
              <Loader size="lg" type="bars" />
              <Text c="dimmed">Calculating tax liability, please wait...</Text>
            </Stack>
          </Center>
        )}
        {results && !loading && <ResultsPane data={results} onRecalculate={handleRecalculate} />}
      </AppShell.Main>
    </AppShell>
  );
}
