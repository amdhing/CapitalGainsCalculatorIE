import { useState, useRef } from 'react';
import {
  Card, Button, Text, Group, Stack, Select, Table,
  Loader, Tooltip, ActionIcon, Collapse,
} from '@mantine/core';
import {
  IconUpload, IconCalculator, IconX, IconFile,
  IconChevronDown, IconChevronRight,
} from '@tabler/icons-react';
import { uploadFile, calculate, CalculateResponse } from '../api/client';

interface UploadedFile {
  file_id: string;
  filename: string;
  rows: number;
}

interface Props {
  onResults: (r: CalculateResponse, fileIds?: string[]) => void;
  onLoading: (v: boolean) => void;
  onError: (e: string | null) => void;
}

export default function UploadPane({ onResults, onLoading, onError }: Props) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [marginRate, setMarginRate] = useState<string | null>('40');
  const [uploading, setUploading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [uploadCollapsed, setUploadCollapsed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasResults = files.length > 0 && uploadCollapsed;

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;
    setUploading(true);
    onError(null);
    try {
      const uploads: UploadedFile[] = [];
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const resp = await uploadFile(file);
        uploads.push({ file_id: resp.file_id, filename: resp.filename, rows: resp.rows });
      }
      setFiles((prev) => [...prev, ...uploads]);
    } catch (err) {
      onError(String(err));
    }
    setUploading(false);
    if (inputRef.current) inputRef.current.value = '';
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.file_id !== fileId));
  };

  const handleCalculate = async () => {
    if (files.length === 0) return;
    setCalculating(true);
    onLoading(true);
    onError(null);
    try {
      const resp = await calculate(
        files.map((f) => f.file_id),
        Number(marginRate) || 40,
      );
      onResults(resp, files.map((f) => f.file_id));
      // Collapse upload section after successful calculation
      setUploadCollapsed(true);
    } catch (err) {
      onError(String(err));
    }
    setCalculating(false);
    onLoading(false);
  };

  return (
    <Stack>
      {/* Upload card — collapsible after calculation */}
      <Card withBorder shadow="sm" p="lg">
        <Group
          justify="space-between"
          onClick={() => setUploadCollapsed((c) => !c)}
          style={{ cursor: 'pointer' }}
        >
          <Group gap="xs">
            {hasResults ? <IconChevronRight size={18} /> : <IconChevronDown size={18} />}
            <Text fw={500}>1. Upload transaction files (Excel or CSV)</Text>
          </Group>
          {files.length > 0 && (
            <Text size="sm" c="dimmed">
              {files.length} file{files.length !== 1 ? 's' : ''} uploaded
            </Text>
          )}
        </Group>

        <Collapse in={!uploadCollapsed}>
          <Stack mt="md">
            <Group>
              <Button
                leftSection={<IconUpload size={16} />}
                onClick={() => inputRef.current?.click()}
                loading={uploading}
              >
                {uploading ? 'Uploading...' : 'Upload Files'}
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                multiple
                hidden
                onChange={handleUpload}
              />
            </Group>

            {files.length > 0 && (
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>File</Table.Th>
                    <Table.Th>Rows</Table.Th>
                    <Table.Th w={60}></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {files.map((f) => (
                    <Table.Tr key={f.file_id}>
                      <Table.Td>
                        <Group gap="xs">
                          <IconFile size={14} />
                          {f.filename}
                        </Group>
                      </Table.Td>
                      <Table.Td>{f.rows}</Table.Td>
                      <Table.Td>
                        <Tooltip label="Remove file">
                          <ActionIcon variant="subtle" color="gray" size="sm" onClick={() => removeFile(f.file_id)}>
                            <IconX size={14} />
                          </ActionIcon>
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Stack>
        </Collapse>
      </Card>

      {/* Parameters card — also collapsible after results */}
      <Card withBorder shadow="sm" p="lg">
        <Stack>
          <Text fw={500}>2. Set tax parameters and calculate</Text>
          <Group>
            <Select
              label="Your marginal income tax rate"
              data={['20', '40', '45']}
              value={marginRate}
              onChange={setMarginRate}
              w={200}
            />
          </Group>
          <Button
            leftSection={calculating ? <Loader size="sm" color="white" /> : <IconCalculator size={16} />}
            onClick={handleCalculate}
            disabled={files.length === 0 || calculating}
            color="teal"
            size="lg"
          >
            {calculating ? 'Calculating...' : 'Calculate Tax'}
          </Button>
        </Stack>
      </Card>
    </Stack>
  );
}
