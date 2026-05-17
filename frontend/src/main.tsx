import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import App from './App';
import '@mantine/core/styles.css';

const theme = createTheme({
  primaryColor: 'teal',
  defaultRadius: 'md',
  colors: {
    teal: [
      '#f3fcfa',
      '#c3f0e6',
      '#94e4d2',
      '#65d8be',
      '#3cccab',
      '#23c099',
      '#1a947a',
      '#126c5a',
      '#0a4539',
      '#031d18',
    ],
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <App />
    </MantineProvider>
  </React.StrictMode>
);
