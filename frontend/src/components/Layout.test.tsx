// src/components/Layout.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './Layout';

// Mock the auth store
vi.mock('../services/authStore', () => ({
  useAuthStore: () => ({
    user: { username: 'testuser' },
    logout: vi.fn(),
  }),
}));

describe('Layout', () => {
  it('renders the main layout and navigation', () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Layout />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Check for the brand link
    expect(screen.getByText('United Degenerates League')).toBeInTheDocument();

    // Check for a navigation link
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    
    // Check for the user's name
    expect(screen.getByText('testuser')).toBeInTheDocument();

    // Check for the main content outlet area (via role)
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
