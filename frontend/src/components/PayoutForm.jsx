import React, { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

function PayoutForm({ apiKey, onSuccess }) {
  const [amount, setAmount] = useState('')
  const [bankAccountId, setBankAccountId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)

    const idempotencyKey = crypto.randomUUID()
    const amountPaise = Math.round(parseFloat(amount) * 100)

    try {
      const response = await fetch(`${API_BASE}/api/v1/payouts/`, {
        method: 'POST',
        headers: {
          'Authorization': `Api-Key ${apiKey}`,
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({
          amount_paise: amountPaise,
          bank_account_id: bankAccountId,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setResult({ type: 'success', message: `Payout created! Status: ${data.status}` })
        setAmount('')
        setBankAccountId('')
        onSuccess()
      } else {
        setResult({ type: 'error', message: data.error || 'Failed to create payout' })
      }
    } catch (err) {
      setResult({ type: 'error', message: err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Payout</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount (INR)
          </label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. 100.00"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bank Account ID
          </label>
          <input
            type="text"
            required
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. acc-123"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-2 rounded-md hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Processing...' : 'Submit Payout'}
        </button>
      </form>
      {result && (
        <div
          className={`mt-4 p-3 rounded text-sm ${
            result.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {result.message}
        </div>
      )}
    </div>
  )
}

export default PayoutForm
