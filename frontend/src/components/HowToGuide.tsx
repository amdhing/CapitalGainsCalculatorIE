import {
  Card, Text, Stack, Title, Group, Anchor, Tabs, List, ThemeIcon,
} from '@mantine/core';
import {
  IconInfoCircle, IconExternalLink, IconFileDescription,
  IconCalendarDue, IconCalculator, IconDeviceDesktopAnalytics,
  IconAlertCircle,
} from '@tabler/icons-react';

export default function HowToGuide() {
  return (
    <Stack my="lg">
      <Title order={3}>How-To Guide: Filing Your Taxes</Title>
      <Text c="dimmed" size="sm">
        Step-by-step instructions for paying Capital Gains Tax and ETF Exit Tax in Ireland
        based on Revenue.ie guidelines.
      </Text>

      <Tabs defaultValue="cgt-current">
        <Tabs.List>
          <Tabs.Tab value="cgt-current" leftSection={<IconCalendarDue size={16} />}>
            CGT – Current Year
          </Tabs.Tab>
          <Tabs.Tab value="cgt-prior" leftSection={<IconFileDescription size={16} />}>
            CGT – Prior Year (CG1)
          </Tabs.Tab>
          <Tabs.Tab value="etf" leftSection={<IconCalculator size={16} />}>
            ETF Exit Tax
          </Tabs.Tab>
          <Tabs.Tab value="how-calc" leftSection={<IconDeviceDesktopAnalytics size={16} />}>
            How Calculations Work
          </Tabs.Tab>
        </Tabs.List>

        {/* ─────────────────────── CGT CURRENT YEAR ─────────────────────── */}
        <Tabs.Panel value="cgt-current" pt="md">
          <CgtCurrentYearPanel />
        </Tabs.Panel>

        {/* ─────────────────────── CGT PRIOR YEAR (CG1) ─────────────────── */}
        <Tabs.Panel value="cgt-prior" pt="md">
          <CgtPriorYearPanel />
        </Tabs.Panel>

        {/* ─────────────────────── ETF EXIT TAX ──────────────────────────── */}
        <Tabs.Panel value="etf" pt="md">
          <EtfPanel />
        </Tabs.Panel>

        {/* ─────────────────────── HOW CALCULATIONS WORK ─────────────────── */}
        <Tabs.Panel value="how-calc" pt="md">
          <HowCalculationsWorkPanel />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

/* ────────────────────────────────────────────────────────────────────────
   CGT – Current Year via myAccount
   ──────────────────────────────────────────────────────────────────────── */

function CgtCurrentYearPanel() {
  return (
    <Stack gap="md">
      <InfoCard
        title="Paying CGT for the Current Tax Year"
        subtitle="Revenue's myAccount — online filing for same-year gains"
      >
        <Text size="sm">
          If you sold shares (stocks) this year and realised a gain, Preliminary
          CGT is due by <strong>15 December</strong> for disposals between
          1 January and 30 November, and by <strong>31 January</strong> for
          disposals in December. Use the calculator above to determine how much
          you owe, then follow the steps below to pay via Revenue's myAccount.
        </Text>
      </InfoCard>

      <StepCard
        step={1}
        title="Log in to Revenue myAccount"
        icon={<IconDeviceDesktopAnalytics size={20} />}
      >
        <Text size="sm">
          Go to{' '}
          <Anchor href="https://www.ros.ie/myaccount-web/sign_in.html" target="_blank" size="sm">
            ROS &ndash; myAccount Sign In
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>{' '}
          and sign in with your Personal Public Service Number (PPSN) and password.
        </Text>
      </StepCard>

      <StepCard
        step={2}
        title="Navigate to 'Make a Payment'"
        icon={<IconInfoCircle size={20} />}
      >
        <Text size="sm">
          Once logged in, look for the <strong>"Make a Payment"</strong> option
          in the menu. Select <strong>"Capital Gains Tax (CGT)"</strong> as the
          payment type.
        </Text>
      </StepCard>

      <StepCard
        step={3}
        title="Enter the Amount from the Calculator"
        icon={<IconCalculator size={20} />}
      >
        <Text size="sm">
          Enter the <strong>Stock CGT liability</strong> amount shown in the
          calculator results (the "Tax Due" figure under Stock CGT Summary,
          after accounting for any tax already paid). This is your Preliminary
          CGT payment.
        </Text>
      </StepCard>

      <StepCard
        step={4}
        title="Choose Payment Method & Confirm"
        icon={<IconCalendarDue size={20} />}
      >
        <Text size="sm">
          You can pay by:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Debit/Credit Card</strong> &ndash; instant payment, small
            surcharge applies.
          </List.Item>
          <List.Item>
            <strong>Direct Debit</strong> &ndash; set up a single or recurring
            payment.
          </List.Item>
          <List.Item>
            <strong>Bank Transfer</strong> &ndash; use the Revenue bank details
            provided on screen.
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          After confirmation, you'll receive a receipt. Save this for your records.
        </Text>
      </StepCard>

      <StepCard
        step={5}
        title="File your CGT Return (by 31 October or 15 November)"
        icon={<IconFileDescription size={20} />}
      >
        <Text size="sm">
          Even after paying, you still need to file a CGT return. In myAccount,
          go to <strong>"Review your tax" → "Capital Gains Tax"</strong> and
          complete the return with your total gains, losses, and exemption details.
          The deadline is <strong>31 October</strong> (paper) or{' '}
          <strong>15 November</strong> (online via myAccount) following the
          tax year.
        </Text>
      </StepCard>

      <WarningCard>
        <Text size="sm">
          <strong>Late payment interest:</strong> Revenue charges interest of
          0.0274% per day (approx. 10% per year) on late CGT payments.
          A surcharge of 5%–10% applies on late returns. Always pay by the
          deadline even if you haven't filed the return yet.
        </Text>
      </WarningCard>
    </Stack>
  );
}

/* ────────────────────────────────────────────────────────────────────────
   CGT – Prior Year via Form CG1
   ──────────────────────────────────────────────────────────────────────── */

function CgtPriorYearPanel() {
  return (
    <Stack gap="md">
      <InfoCard
        title="Filing CGT for a Previous Tax Year"
        subtitle="Form CG1 — for gains from prior years not yet reported"
      >
        <Text size="sm">
          If you sold shares in a <strong>previous tax year</strong> and didn't
          report the gains yet (e.g. you're catching up on old trades), you need
          to file a <strong>CG1</strong> return. This applies whether you made
          a gain or a loss. The calculator above handles multiple years &ndash;
          just upload all your transaction files and it will break down each year.
        </Text>
      </InfoCard>

      <StepCard
        step={1}
        title="Download Form CG1"
        icon={<IconFileDescription size={20} />}
      >
        <Text size="sm">
          Download the relevant CG1 form from Revenue's website:{' '}
          <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/documents/formcg1.pdf" target="_blank" size="sm">
            CG1 – Current Year (PDF)
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
          {' | '}
          <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/documents/form-cg1-2024.pdf" target="_blank" size="sm">
            2024 (PDF)
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
          {' | '}
          <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/documents/formcg1-2023.pdf" target="_blank" size="sm">
            2023 (PDF)
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
          {' | '}
          <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/documents/formcg1-2022.pdf" target="_blank" size="sm">
            2022 (PDF)
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
          {' | '}
          <Anchor href="https://www.revenue.ie/en/gains-gifts-and-inheritance/documents/formcg1-2021.pdf" target="_blank" size="sm">
            2021 (PDF)
            <IconExternalLink size={12} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
        </Text>
      </StepCard>

      <StepCard
        step={2}
        title="Gather Your Calculator Results"
        icon={<IconCalculator size={20} />}
      >
        <Text size="sm">
          Use the calculator above with all your transactions uploaded. For each
          year, note down:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>Total disposal proceeds (sales)</List.Item>
          <List.Item>Total allowable costs (acquisition cost + fees)</List.Item>
          <List.Item>Gain or loss per disposal</List.Item>
          <List.Item>Annual exemption applied (€1,270)</List.Item>
          <List.Item>Losses brought forward / carried forward</List.Item>
          <List.Item>Net taxable gain and CGT due</List.Item>
        </List>
      </StepCard>

      <StepCard
        step={3}
        title="Complete the CG1 Form"
        icon={<IconInfoCircle size={20} />}
      >
        <Text size="sm">
          The CG1 form uses numbered sections. For share disposals the key ones are:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Section 1 (Description of Assets):</strong> enter aggregate
            consideration for <em>Shares / Securities — Quoted</em> (and
            <em>Unquoted</em> if applicable) from the calculator's ticker breakdown.
          </List.Item>
          <List.Item>
            <strong>Section 10 / 11 (Chargeable gains & losses):</strong>
            the calculator's net chargeable gain and any losses.
          </List.Item>
          <List.Item>
            <strong>Section 26 (Double Taxation Relief):</strong> claim credit
            for any foreign tax withheld (list country, gain, and tax).
          </List.Item>
          <List.Item>
            <strong>Section 28 (Self-Assessment):</strong> the final CGT
            liability for that year.
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          The €1,270 annual exemption is applied within the chargeable-gain
          calculation (Section 10); there is no separate "exemption" box.
        </Text>
      </StepCard>

      <StepCard
        step={4}
        title="Submit & Pay"
        icon={<IconCalendarDue size={20} />}
      >
        <Text size="sm">
          Submit the completed CG1 to Revenue via:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>myAccount</strong> &ndash; upload the form under
            "Upload Documents" (fastest).
          </List.Item>
          <List.Item>
            <strong>Post</strong> &ndash; send to your local Revenue office.
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          Pay any tax due using the same methods as above. If you already paid
          preliminary CGT for that year, enter the amount paid on the form to
          calculate your balance.
        </Text>
      </StepCard>

      <NoteCard>
        <Text size="sm">
          <strong>Foreign gains & foreign tax credit (CG1):</strong> report
          foreign share gains in the same Schedules as Irish gains — there is no
          separate "foreign gains" box. If foreign tax was withheld at source,
          claim it under <strong>Section 26 "Double Taxation Relief"</strong>{' '}
          (list the country, the gain, and the foreign tax).
        </Text>
      </NoteCard>

      <NoteCard>
        <Text size="sm">
          <strong>Loss carry forward:</strong> If the calculator shows losses
          carried forward for a year, those losses can offset future gains
          indefinitely. Make sure you report losses on your CG1 even if you
          don't owe any tax &ndash; Revenue needs to see them to allow the
          carry forward.
        </Text>
      </NoteCard>
    </Stack>
  );
}

/* ────────────────────────────────────────────────────────────────────────
   ETF Exit Tax
   ──────────────────────────────────────────────────────────────────────── */

function EtfPanel() {
  return (
    <Stack gap="md">
      <InfoCard
        title="Paying ETF Exit Tax"
        subtitle="Form CG2 / Form 11 — for ETF gains, dividends, and deemed disposals"
      >
        <Text size="sm">
          Irish residents who hold offshore ETFs are subject to{' '}
          <strong>exit tax</strong> (41% up to 2025, 38% from 2026) rather than
          CGT. This applies to:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>Realised gains when you sell ETF units</List.Item>
          <List.Item>ETF dividend distributions</List.Item>
          <List.Item>Deemed disposal gains (8-year rule)</List.Item>
        </List>
      </InfoCard>

      <StepCard
        step={1}
        title="Identify Your ETF Transactions"
        icon={<IconCalculator size={20} />}
      >
        <Text size="sm">
          Use the calculator above with your transaction history. The results
          will show a separate <strong>ETF Exit Tax Summary</strong> section
          breaking down gains, dividends, and tax due per year. Note that ETFs
          are taxed independently per ticker &ndash; losses on one ETF cannot
          offset gains on another.
        </Text>
      </StepCard>

      <StepCard
        step={2}
        title="Choose the Right Form"
        icon={<IconFileDescription size={20} />}
      >
        <Text size="sm">
          How you report ETF exit tax depends on your filing status:
        </Text>
        <Card withBorder p="sm" mt="xs" bg="dark.7">
          <Stack gap="xs">
            <Group gap="xs">
              <ThemeIcon color="teal" size={20} radius="xl">
                <Text size="xs" fw={700}>A</Text>
              </ThemeIcon>
              <Text size="sm" fw={600}>If you file a Form 11 (self-assessment):</Text>
            </Group>
            <Text size="sm" pl="lg">
              Enter the ETF exit tax details in the <strong>ETF section</strong> of your
              Form 11. Include gains, dividends, and deemed disposals under
              "Offshore Funds" or "Investment Funds" as applicable.
            </Text>
          </Stack>
        </Card>
        <Card withBorder p="sm" mt="xs" bg="dark.7">
          <Stack gap="xs">
            <Group gap="xs">
              <ThemeIcon color="yellow" size={20} radius="xl">
                <Text size="xs" fw={700}>B</Text>
              </ThemeIcon>
              <Text size="sm" fw={600}>If you use myAccount (PAYE):</Text>
            </Group>
            <Text size="sm" pl="lg">
              Download and file <strong>Form CG2</strong> (return of chargeable
              gains for offshore funds). This form specifically covers ETF exit
              tax and deemed disposals.
            </Text>
          </Stack>
        </Card>
      </StepCard>

      <StepCard
        step={3}
        title="Complete the Return"
        icon={<IconInfoCircle size={20} />}
      >
        <Text size="sm">
          For each ETF holding, report:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Name of fund</strong> and ISIN (if known)
          </List.Item>
          <List.Item>
            <strong>Disposal proceeds</strong> &ndash; from the calculator's
            ticker breakdown (Gain column for ETFs)
          </List.Item>
          <List.Item>
            <strong>Acquisition cost</strong> &ndash; what you paid (the
            calculator handles FIFO cost basis)
          </List.Item>
          <List.Item>
            <strong>Gain or loss</strong> &ndash; per the calculator
          </List.Item>
          <List.Item>
            <strong>Dividends received</strong> &ndash; shown in the Div Total
            column
          </List.Item>
          <List.Item>
            <strong>Deemed disposal</strong> &ndash; if you've held an ETF
            for 8+ years, report the deemed gain (the calculator estimates
            this in the current holdings section)
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          <strong>Key distinction:</strong> ETF dividends are taxed at the exit
          tax rate (41%/38%) &ndash; <em>not</em> at your marginal income tax rate.
          Do not include ETF dividends on your income tax return; they go on the
          ETF return.
        </Text>
      </StepCard>

      <StepCard
        step={4}
        title="Pay the Exit Tax"
        icon={<IconCalendarDue size={20} />}
      >
        <Text size="sm">
          ETF exit tax is due by the same deadlines as CGT:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Preliminary tax:</strong> 15 November of the current year
            (or 15 December if filing online)
          </List.Item>
          <List.Item>
            <strong>Final return:</strong> 31 October (paper) / 15 November
            (online) of the following year
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          Make the payment via myAccount under <strong>"Make a Payment" → "Capital Gains Tax"</strong>.
          Even though it's called "Capital Gains Tax" in myAccount, exit tax on
          ETFs is paid through the same mechanism.
        </Text>
      </StepCard>

      <StepCard
        step={5}
        title="Handle Deemed Disposal (8-Year Rule)"
        icon={<IconAlertCircle size={20} />}
      >
        <Text size="sm">
          If you've held an ETF for 8 years or more, you're deemed to have sold
          and immediately repurchased it. The tax paid at that point becomes a
          credit against the final tax when you actually sell.
        </Text>
        <Card withBorder p="sm" mt="xs" bg="dark.7">
          <Text size="sm">
            <strong>Example:</strong><br />
            You bought an ETF for €10,000 in 2017.<br />
            In 2025 (year 8): Value is €14,000 → Deemed gain = €4,000 → Exit
            tax @ 41% = €1,640.<br />
            Pay the €1,640 now. Your cost basis resets to €14,000.<br />
            You sell in 2027 for €15,000 → Actual gain = €1,000 → Exit tax @
            38% = €380.<br />
            Total tax = €1,640 + €380 = €2,020 = 38% of €5,000 total gain ✓
          </Text>
        </Card>
      </StepCard>

      <WarningCard>
        <Text size="sm">
          <strong>No loss relief between ETFs:</strong> If you make a loss on one
          ETF and a gain on another, you cannot offset them. Each ETF is taxed
          independently. The calculator handles this correctly &ndash; check the
          per-ticker breakdown for details.
        </Text>
      </WarningCard>

      <NoteCard>
        <Text size="sm">
          <strong>Deemed disposal & the 2026 rate change:</strong> From 2026
          onward the exit tax rate drops to 38%. If your 8-year anniversary falls
          in 2026 or later, the deemed disposal is calculated at 38%. The
          calculator applies the correct rate based on the year.
        </Text>
      </NoteCard>

      <Card withBorder shadow="sm" p="sm" bg="dark.7">
        <Group gap="xs">
          <Anchor href="https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-27/27-01a-03.pdf" target="_blank" size="xs">
            Revenue Tax Manual – Offshore Funds (Part 27-01a-03)
            <IconExternalLink size={10} style={{ marginLeft: 4, verticalAlign: 'middle' }} />
          </Anchor>
        </Group>
      </Card>
    </Stack>
  );
}

/* ────────────────────────────────────────────────────────────────────────
   How Calculations Work
   ──────────────────────────────────────────────────────────────────────── */

function HowCalculationsWorkPanel() {
  return (
    <Stack gap="md">
      <InfoCard
        title="How This Calculator Works"
        subtitle="Same FIFO cost-basis engine, regardless of which broker the file came from"
      >
        <Text size="sm">
          Every uploaded file is normalised into one internal format, then run
          through the same Irish tax engine. This means Revolut, Zerodha, and
          future brokers are all treated consistently — and can even be mixed in
          a single calculation.
        </Text>
      </InfoCard>

      <StepCard step={1} title="Broker files are normalised" icon={<IconFileDescription size={20} />}>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Revolut</strong> — read directly (it already includes trade
            date, quantity, price, total, currency, and FX rate).
          </List.Item>
          <List.Item>
            <strong>Zerodha</strong> — the Indian tradebook (Symbol, ISIN, Trade
            Date, Trade Type, Quantity, Price) is mapped to the same format. INR
            is converted to EUR automatically.
          </List.Item>
          <List.Item>
            <strong>Trading 212</strong> — format researched; full parsing is on
            the roadmap.
          </List.Item>
        </List>
      </StepCard>

      <StepCard step={2} title="Everything is converted to EUR" icon={<IconCalculator size={20} />}>
        <Text size="sm">
          Irish taxes are calculated in EUR. For Revolut, the file's own FX rate
          is used. For Zerodha (INR), the app fetches{' '}
          <strong>one current INR→EUR rate from yfinance</strong> and applies it.
        </Text>
        <Text size="xs" c="dimmed">
          Note: a single current rate is applied across all Zerodha trades — a
          known simplification tracked for improvement (per-trade-date rates).
        </Text>
      </StepCard>

      <StepCard step={3} title="Stocks vs ETFs are classified" icon={<IconInfoCircle size={20} />}>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Stocks</strong> → Capital Gains Tax (33%, €1,270 exemption,
            loss carry-forward).
          </List.Item>
          <List.Item>
            <strong>Irish UCITS and "equivalent" offshore funds</strong> (EU/EEA/
            OECD UCITS-like funds) → Exit Tax (41% to 2025, 38% from 2026), no
            exemption, no loss relief, 8-year deemed disposal.
          </List.Item>
          <List.Item>
            <strong>Offshore funds outside the EU/EEA/OECD</strong> — e.g.
            Indian-domiciled ETFs such as Zerodha <em>*BEES</em>, <em>GOLDETF</em>{' '}
            — are non-distributing offshore funds. Their disposal gains are taxed
            as <strong>Case IV income</strong> at your marginal rate (no €1,270
            exemption, losses ignored), not as CGT and not at the 38% exit-tax
            rate.
          </List.Item>
        </List>
        <Text size="xs" c="dimmed">
          India is not an OECD member and lies outside the EU/EEA, so the Chapter
          4 "equivalent fund" exit-tax regime does not apply. The app applies the
          Chapter 2 Case IV treatment. Verify with a tax advisor.
        </Text>
      </StepCard>

      <StepCard step={4} title="Gains use FIFO cost basis" icon={<IconCalculator size={20} />}>
        <Text size="sm">
          Shares sold are matched against your oldest buys first (first-in,
          first-out). Merger conversions, broker transfers, and inactive
          (delisted) securities are accounted for.
        </Text>
      </StepCard>

      <StepCard step={5} title="Foreign-situs gains use your domicile status" icon={<IconInfoCircle size={20} />}>
        <Text size="sm">
          Irish CGT on <strong>non-Irish</strong> assets depends on your{' '}
          <strong>domicile</strong>, not citizenship:
        </Text>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Domiciled (arising basis)</strong> — the full worldwide gain
            is taxed in Ireland, even if not remitted.
          </List.Item>
          <List.Item>
            <strong>Non-domiciled (remittance basis)</strong> — only foreign
            gains <em>remitted to Ireland</em> are taxed.
          </List.Item>
        </List>
        <Text size="sm" mt="xs">
          Irish-situs assets (domiciled <em>IE</em>) are always taxable. Set your
          domicile status in the tax parameter card before calculating.
        </Text>
      </StepCard>

      <StepCard step={6} title="Results are summarised three ways" icon={<IconDeviceDesktopAnalytics size={20} />}>
        <List spacing="xs" size="sm">
          <List.Item>
            <strong>Per-Source Summary</strong> — one line per broker per year
            (gains + dividends), with a chart.
          </List.Item>
          <List.Item>
            <strong>Stock CGT / ETF Tax Summary</strong> — the consolidated Irish
            tax liability tables.
          </List.Item>
          <List.Item>
            <strong>Per-Ticker Breakdown</strong> — individual securities, all in
            EUR (their native currency is shown as a badge).
          </List.Item>
        </List>
      </StepCard>

      <NoteCard>
        <Text size="sm">
          <strong>Indian double-taxation:</strong> under the Ireland–India treaty
          (Art. 13), for an Irish tax resident Ireland has the primary right to tax
          share disposals. Indian tax withheld at source can be entered as "Already
          Paid" to offset your Irish liability.
        </Text>
      </NoteCard>
    </Stack>
  );
}

/* ────────────────────────────────────────────────────────────────────────
   Shared UI components
   ──────────────────────────────────────────────────────────────────────── */

function InfoCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card withBorder shadow="sm" p="lg" bg="dark.7">
      <Stack gap={6}>
        <Group gap="xs">
          <ThemeIcon color="teal" size={24} radius="xl">
            <IconInfoCircle size={16} />
          </ThemeIcon>
          <Text fw={600} size="lg">{title}</Text>
        </Group>
        {subtitle && <Text size="sm" c="dimmed">{subtitle}</Text>}
        {children}
      </Stack>
    </Card>
  );
}

function StepCard({ step, title, icon, children }: { step: number; title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card withBorder shadow="sm" p="lg">
      <Stack gap="xs">
        <Group gap="xs">
          <ThemeIcon color="teal" size={28} radius="xl">
            <Text fw={700} size="sm">{step}</Text>
          </ThemeIcon>
          {icon}
          <Text fw={600} size="md">{title}</Text>
        </Group>
        {children}
      </Stack>
    </Card>
  );
}

function WarningCard({ children }: { children: React.ReactNode }) {
  return (
    <Card withBorder shadow="sm" p="md" bg="rgba(230, 126, 34, 0.1)" style={{ borderColor: '#e67e22' }}>
      <Group gap="xs">
        <IconAlertCircle size={20} color="#e67e22" />
        <Text fw={600} c="orange">Important</Text>
      </Group>
      {children}
    </Card>
  );
}

function NoteCard({ children }: { children: React.ReactNode }) {
  return (
    <Card withBorder shadow="sm" p="md" bg="rgba(54, 162, 235, 0.08)" style={{ borderColor: '#3692eb' }}>
      <Group gap="xs">
        <IconInfoCircle size={20} color="#3692eb" />
        <Text fw={600} c="blue">Note</Text>
      </Group>
      {children}
    </Card>
  );
}
