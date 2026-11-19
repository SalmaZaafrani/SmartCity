import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';

const SocketContext = createContext();
export const useSocket = () => useContext(SocketContext);

const SOCKET_URL = 'http://localhost:5000';
const MAX_ALERTS = 50;

export const SocketProvider = ({ children }) => {
  const [socket, setSocket]           = useState(null);
  const [connected, setConnected]     = useState(false);
  const [lastAlert, setLastAlert]     = useState(null);
  const [aiReport, setAiReport]       = useState(null);
  const [metrics, setMetrics]         = useState(null);
  const [alerts, setAlerts]           = useState([]);   // historique alertes
  const [statusChange, setStatusChange] = useState(null);
  const reconnectTimer = useRef(null);

  const addAlert = useCallback((alert) => {
    const enriched = { ...alert, timestamp: new Date().toISOString(), id: Date.now() };
    setLastAlert(enriched);
    setAlerts(prev => [enriched, ...prev].slice(0, MAX_ALERTS));
  }, []);

  const connect = useCallback(() => {
    const sock = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
      timeout: 10000,
    });

    sock.on('connect', () => {
      console.log('✅ WebSocket Connected:', sock.id);
      setConnected(true);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    });

    sock.on('disconnect', (reason) => {
      console.warn('❌ WebSocket Disconnected:', reason);
      setConnected(false);
    });

    sock.on('connect_error', (err) => {
      console.error('🔌 Connection error:', err.message);
      setConnected(false);
    });

    // Métriques temps réel (toutes les 10s depuis le serveur)
    sock.on('metrics_update', (data) => {
      setMetrics(data);
    });

    // Alertes (capteurs HS, interventions en retard)
    sock.on('alert', (data) => {
      addAlert(data);
    });

    // Rapport IA automatique
    sock.on('ai_report', (data) => {
      setAiReport(data);
    });

    // Changement de statut automate
    sock.on('status_change', (data) => {
      setStatusChange(data);
      addAlert({
        type: 'automate',
        message: `Statut mis à jour : ${data.entite} → ${data.new_state}`,
        ...data,
      });
    });

    setSocket(sock);
    return sock;
  }, [addAlert]);

  useEffect(() => {
    const sock = connect();
    return () => {
      sock.disconnect();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  // Méthode pour envoyer un événement au serveur
  const emit = useCallback((event, data) => {
    if (socket?.connected) {
      socket.emit(event, data);
    }
  }, [socket]);

  // Effacer les alertes
  const clearAlerts = useCallback(() => {
    setAlerts([]);
    setLastAlert(null);
  }, []);

  return (
    <SocketContext.Provider value={{
      socket,
      connected,
      lastAlert,
      aiReport,
      metrics,
      alerts,
      statusChange,
      emit,
      clearAlerts,
    }}>
      {children}
    </SocketContext.Provider>
  );
};