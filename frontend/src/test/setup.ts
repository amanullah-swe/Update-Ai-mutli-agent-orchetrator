import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// vitest runs without `globals`, so @testing-library/react cannot auto-register
// its afterEach cleanup — without this, rendered DOM accumulates across tests
// in a file and queries start matching elements from earlier tests.
afterEach(() => cleanup())
