// src/pages/Login.js
import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { LogIn, UserPlus, Key } from 'lucide-react';
import AuthAPI from '../services/AuthAPI';
import './Login.css';

const Login = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState('login'); // 'login' veya 'register'
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };
  
  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await AuthAPI.login(formData.email, formData.password);
      if (onLogin) {
        // Credentials'ı da response ile birlikte gönder
        onLogin({
          email: formData.email,
          password: formData.password,
          response: response.data
        });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Giriş yapılırken bir hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRegister = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      setError('Şifreler eşleşmiyor');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      await AuthAPI.register(
        formData.username, 
        formData.email, 
        formData.password
      );
      
      // Kayıt başarılı, giriş ekranına geç
      setActiveTab('login');
      setFormData({
        ...formData,
        password: '',
        confirmPassword: ''
      });
      setError(null);
      
    } catch (err) {
      setError(err.response?.data?.message || 'Kayıt olurken bir hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Container fluid className="login-container">
      <Row className="justify-content-center align-items-center min-vh-100">
        <Col md={6} lg={4}>
          <Card className="login-card shadow">
            <Card.Body className="p-4">
              <div className="text-center mb-4">
                <img src="/logo192.png" alt="Metis Agent" className="login-logo" width="80" />
                <h2 className="mt-3">Metis Agent</h2>
                <p className="text-muted">Akıllı asistanınıza hoş geldiniz</p>
              </div>
              
              <div className="d-flex mb-4">
                <Button 
                  variant={activeTab === 'login' ? 'primary' : 'light'}
                  className="flex-grow-1 me-2"
                  onClick={() => setActiveTab('login')}
                >
                  <LogIn size={16} className="me-2" />
                  Giriş
                </Button>
                <Button 
                  variant={activeTab === 'register' ? 'primary' : 'light'}
                  className="flex-grow-1"
                  onClick={() => setActiveTab('register')}
                >
                  <UserPlus size={16} className="me-2" />
                  Kayıt
                </Button>
              </div>
              
              {error && <Alert variant="danger">{error}</Alert>}
              
              {activeTab === 'login' ? (
                <Form onSubmit={handleLogin}>
                  <Form.Group className="mb-3">
                    <Form.Label>E-posta</Form.Label>
                    <Form.Control
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="ornek@email.com"
                      required
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-4">
                    <Form.Label>Şifre</Form.Label>
                    <Form.Control
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                    />
                  </Form.Group>
                  
                  <Button 
                    variant="primary" 
                    type="submit" 
                    className="w-100"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      <>
                        <LogIn size={16} className="me-2" />
                        Giriş Yap
                      </>
                    )}
                  </Button>
                </Form>
              ) : (
                <Form onSubmit={handleRegister}>
                  <Form.Group className="mb-3">
                    <Form.Label>Kullanıcı Adı</Form.Label>
                    <Form.Control
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      required
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-3">
                    <Form.Label>E-posta</Form.Label>
                    <Form.Control
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-3">
                    <Form.Label>Şifre</Form.Label>
                    <Form.Control
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-4">
                    <Form.Label>Şifre Tekrar</Form.Label>
                    <Form.Control
                      type="password"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      required
                    />
                  </Form.Group>
                  
                  <Button 
                    variant="primary" 
                    type="submit" 
                    className="w-100"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      <>
                        <UserPlus size={16} className="me-2" />
                        Kayıt Ol
                      </>
                    )}
                  </Button>
                </Form>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Login;