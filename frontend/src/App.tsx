import { useState, useCallback } from 'react';
import { AppShell, Group, Title, Text, Loader, Center, Stack, Anchor, Card, Button } from '@mantine/core';

import { IconCurrencyEuro, IconBrandGithub, IconBrandLinkedin, IconExternalLink, IconBook2, IconCalculator } from '@tabler/icons-react';
import UploadPane from './components/UploadPane';
import ResultsPane from './components/ResultsPane';
import HowToGuide from './components/HowToGuide';
import { CalculateResponse, calculate, PriorTaxPaid } from './api/client';

export default function App() {
  const [results, setResults] = useState<CalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileIds, setFileIds] = useState<string[]>([]);
  const [showGuide, setShowGuide] = useState(false);

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
        <Group h="100%" px="md" justify="apart">
          <Group>
            <IconCurrencyEuro size={28} />
            <Title order={3}>Irish Capital Gains Calculator</Title>
          </Group>
          <Button
            variant="subtle"
            size="sm"
            leftSection={showGuide ? <IconCalculator size={18} /> : <IconBook2 size={18} />}
            onClick={() => setShowGuide((v) => !v)}
          >
            {showGuide ? 'Calculator' : 'How-To Guide'}
          </Button>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {showGuide ? (
          <HowToGuide />
        ) : (
          <>
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
          </>
        )}

        {/* Footer */}
        <Card withBorder shadow="sm" p="sm" mt="xl">
          <Stack gap={4} align="center">
            <Group gap="sm" justify="center">
              <Text size="sm" fw={600}>Built by Aman Dhingra</Text>
              <Anchor href="https://github.com/amdhing" target="_blank" size="sm">
                <Group gap={4}>
                  <IconBrandGithub size={14} />
                  GitHub
                </Group>
              </Anchor>
              <Anchor href="https://www.linkedin.com/in/amdhing" target="_blank" size="sm">
                <Group gap={4}>
                  <IconBrandLinkedin size={14} />
                  LinkedIn
                </Group>
              </Anchor>
            </Group>
            <Group gap="sm" justify="center">
              <Text size="xs" c="dimmed">Tax references:</Text>
              <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/transfering-an-asset/when-and-how-do-you-pay-and-file-cgt.aspx" target="_blank" size="xs">
                <Group gap={4}>
                  Revenue.ie – Pay & File CGT
                  <IconExternalLink size={10} />
                </Group>
              </Anchor>
              <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/transfering-an-asset/how-to-calculate-cgt.aspx" target="_blank" size="xs">
                <Group gap={4}>
                  Revenue.ie – Computing a Gain
                  <IconExternalLink size={10} />
                </Group>
              </Anchor>
              <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/transfering-an-asset/if-you-make-a-loss.aspx" target="_blank" size="xs">
                <Group gap={4}>
                  Revenue.ie – Losses
                  <IconExternalLink size={10} />
                </Group>
              </Anchor>
              <Anchor href="https://www.etf.ie/tax/" target="_blank" size="xs">
                <Group gap={4}>
                  ETF.ie – Tax Guide
                  <IconExternalLink size={10} />
                </Group>
              </Anchor>
            </Group>
            <Text size="xs" c="dimmed" ta="center">
              For informational purposes only. Always verify with a qualified tax advisor.
            </Text>
          </Stack>
        </Card>
      </AppShell.Main>
    </AppShell>
  );

}

