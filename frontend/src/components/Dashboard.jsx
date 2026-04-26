import React, { useState, useEffect, useCallback } from 'react'
import PayoutForm from './PayoutForm'
import PayoutHistory from './PayoutHistory'
import Ledger from './Ledger'

const API_BASE = import.meta.env.VITE_API_URL || ''

function Dashboard({ apiKey }) {
  const [merchant, setMerchant] = useState(null)
  const [payouts, setPayouts] = useState([])
  const [ledger, setLedger] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const headers = {
        'Authorization': `Api-Key ${apiKey}`,
        'Content-Type': 'application/json',
      }

      const [meRes, payoutsRes, ledgerRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/me/`, { headers }),
        fetch(`${API_BASE}/api/v1/payouts/`, { headers }),
        fetch(`${API_BASE}/api/v1/ledger/`, { headers }),
      ])

      if (!meRes.ok) throw new Error('Failed to fetch merchant data')

      const meData = await meRes.json()
      const payoutsData = await payoutsRes.json()
      const ledgerData = await ledgerRes.json()

      setMerchant(meData)
      setPayouts(payoutsData)
      setLedger(ledgerData)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error: {error}
      </div>
    )
  }

  const formatCurrency = (paise) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(paise / 100)
  }

  return (
    <div className="space-y-8">
      {/* Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            Available Balance
          </h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {formatCurrency(merchant?.available_balance_paise || 0)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            Held Balance
          </h3>
          <p className="mt-2 text-3xl font-bold text-orange-600">
            {formatCurrency(merchant?.held_balance_paise || 0)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            Total Balance
          </h3>
          <p className="mt-2 text-3xl font-bold text-indigo-600">
            {formatCurrency(
              (merchant?.available_balance_paise || 0) + (merchant?.held_balance_paise || 0)
            )}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Payout Form */}
        <div>
          <PayoutForm apiKey={apiKey} onSuccess={fetchData} />
        </div>

        {/* Ledger */}
        <div>
          <Ledger entries={ledger} formatCurrency={formatCurrency} />
        </div>
      </div>

      {/* Payout History */}
      <div>
        <PayoutHistory payouts={payouts} formatCurrency={formatCurrency} />
      </div>
    </div>
  )
}

export default Dashboard
