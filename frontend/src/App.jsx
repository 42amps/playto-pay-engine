import React, { useState } from 'react'
import Dashboard from './components/Dashboard'

function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('playto_api_key') || '')
  const [inputKey, setInputKey] = useState(apiKey)

  const handleSetKey = (e) => {
    e.preventDefault()
    localStorage.setItem('playto_api_key', inputKey)
    setApiKey(inputKey)
  }

  const handleLogout = () => {
    localStorage.removeItem('playto_api_key')
    setApiKey('')
    setInputKey('')
  }

  if (!apiKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-2 text-indigo-600">Playto Pay</h1>
          <p className="text-gray-600 mb-6">Enter your API key to access the dashboard</p>
          <form onSubmit={handleSetKey}>
            <input
              type="text"
              value={inputKey}
              onChange={(e) => setInputKey(e.target.value)}
              placeholder="Api-Key ..."
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-4"
            />
            <button
              type="submit"
              className="w-full bg-indigo-600 text-white py-2 rounded-md hover:bg-indigo-700 transition"
            >
              Access Dashboard
            </button>
          </form>
          <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
            <p className="font-semibold mb-1">Demo API Keys:</p>
            <ul className="list-disc list-inside space-y-1">
              <li><code className="bg-gray-200 px-1 rounded">api-key-acme-agency</code> (₹10,000)</li>
              <li><code className="bg-gray-200 px-1 rounded">api-key-freelancer-fiaz</code> (₹5,000)</li>
              <li><code className="bg-gray-200 px-1 rounded">api-key-tiny-studio</code> (₹100)</li>
            </ul>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <h1 className="text-xl font-bold text-indigo-600">Playto Pay</h1>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Change Key
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Dashboard apiKey={apiKey} />
      </main>
    </div>
  )
}

export default App
