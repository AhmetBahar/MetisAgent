// src/components/Chat.js (veya ChatInterface.js)
import React, { useState, useEffect, useRef } from 'react';
import { Card, InputGroup, FormControl, Button, ListGroup } from 'react-bootstrap';
import { Send } from 'lucide-react';
import ChatMessage from './ChatMessage';
import AgentWebSocketService from '../services/AgentWebSocketService';

const Chat = ({ selectedPersona, user }) => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const messagesEndRef = useRef(null);

    useEffect(() => {
        console.log('Chat component mounted, WebSocket durumu:', AgentWebSocketService.isConnected());

        // WebSocket bağlantısını başlat
        if (!AgentWebSocketService.isConnected()) {
            console.log('WebSocket bağlantısı başlatılıyor...');
            AgentWebSocketService.connect();
        }

        // Mesaj yanıtlarını dinle
        const handleMessageResponse = (data) => {
            console.log('WebSocket yanıtı alındı:', data);
            const newMessage = {
                id: Date.now(),
                sender: data.persona_id,
                content: data.response,
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, newMessage]);
        };

        AgentWebSocketService.on('message_response', handleMessageResponse);

        // Cleanup
        return () => {
            // Event listener'ı kaldırmak için off metodu gerekli
        };
    }, []);

    useEffect(() => {
        // Otomatik scroll
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (selectedPersona) {
            // Persona'yı başlat
            AgentWebSocketService.send('start_persona', {
                persona_id: selectedPersona
            });
        }
    }, [selectedPersona]);

    const handleSendMessage = (e) => {
        e.preventDefault();
        if (inputMessage.trim() && selectedPersona) {
            // Kullanıcı mesajını ekle
            const userMessage = {
                id: Date.now(),
                sender: 'user',
                content: inputMessage,
                timestamp: new Date().toISOString()
            };
            
            setMessages(prev => [...prev, userMessage]);
            
            // WebSocket üzerinden persona'ya gönder
            AgentWebSocketService.sendMessage(selectedPersona, inputMessage);
            
            // Input'u temizle
            setInputMessage('');
        }
    };

    return (
        <Card className="chat-container">
            <Card.Header>
                <h5>Chat - {selectedPersona || 'Persona Seçiniz'}</h5>
            </Card.Header>
            <Card.Body className="chat-messages">
                {messages.map((message) => (
                    <ChatMessage 
                        key={message.id} 
                        message={message} 
                        user={user}
                    />
                ))}
                <div ref={messagesEndRef} />
            </Card.Body>
            <Card.Footer>
                <form onSubmit={handleSendMessage}>
                    <InputGroup>
                        <FormControl
                            placeholder="Mesajınızı yazın..."
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            disabled={!selectedPersona}
                        />
                        <Button 
                            type="submit" 
                            variant="primary"
                            disabled={!selectedPersona || !inputMessage.trim()}
                        >
                            <Send size={16} />
                        </Button>
                    </InputGroup>
                </form>
            </Card.Footer>
        </Card>
    );
};

export default Chat;