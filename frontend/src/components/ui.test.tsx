import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../services/api'
import { Banner, ErrorState, Pill } from './ui'

describe('ui components', () => {
  it('renders a pill and a banner', () => {
    render(<><Pill tone="green">normal</Pill><Banner tone="amber" title="Synthetic model">note</Banner></>)
    expect(screen.getByText('normal')).toBeInTheDocument()
    expect(screen.getByText('Synthetic model')).toBeInTheDocument()
  })
  it('explains an unreachable backend and a missing API URL', () => {
    const { rerender } = render(<ErrorState error={new ApiError('unreachable', 'Cannot reach the backend API.')} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Backend not reachable')
    rerender(<ErrorState error={new ApiError('not_configured', 'VITE_API_BASE_URL is not set for this deployment.')} />)
    expect(screen.getByText(/redeploy/)).toBeInTheDocument()
  })
})
