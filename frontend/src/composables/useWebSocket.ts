import { ref, onMounted, onUnmounted } from 'vue'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export interface HitEvent {
  lane: number
  position: string
  accuracy: number
  score: number
  total_score: number
  hit_count: number
  timestamp: string
}

export function useWebSocket(
  url: string,
  onMessage: (msg: WebSocketMessage) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 10

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = url.startsWith('ws') ? url : `${protocol}//${window.location.host}${url}`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket connected')
      isConnected.value = true
      reconnectAttempts.value = 0
      onConnect?.()
    }

    ws.value.onclose = () => {
      console.log('WebSocket disconnected')
      isConnected.value = false
      onDisconnect?.()
      attemptReconnect()
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }

  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    // Don't reconnect too aggressively
    const delay = Math.min(2000 + (reconnectAttempts.value * 1000), 30000)
    console.log(`Attempting to reconnect in ${delay}ms...`)

    setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, delay)
  }

  function send(message: object) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    send,
    connect,
    disconnect
  }
}

export function useDeviceWebSocket(
  deviceId: string,
  onMessage: (msg: WebSocketMessage) => void
) {
  const url = `/ws/device/?device_id=${deviceId}`
  return useWebSocket(url, onMessage)
}

export function useClientWebSocket(
  laneNumber: number,
  onMessage: (msg: WebSocketMessage) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
) {
  const url = `/ws/client/?lane=${laneNumber}`
  return useWebSocket(url, onMessage, onConnect, onDisconnect)
}

export function useAdminWebSocket(
  onMessage: (msg: WebSocketMessage) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
) {
  const url = '/ws/admin/'
  return useWebSocket(url, onMessage, onConnect, onDisconnect)
}
