import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          AlgoTrader Pro
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          멀티마켓 자동 트레이딩 플랫폼
        </p>
        <button
          onClick={() => setCount((count) => count + 1)}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Count is {count}
        </button>
        <p className="mt-4 text-sm text-gray-500">
          🚀 Phase 2: 핵심 인프라 구축 완료!
        </p>
      </div>
    </div>
  )
}

export default App
