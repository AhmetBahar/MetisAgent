// src/components/ReportSummaryModal.js
import React, { useState, useEffect } from 'react';
import { 
  Modal, Button, Card, Form, ProgressBar, Badge, Accordion 
} from 'react-bootstrap';
import { 
  CheckCircle, XCircle, Clock, AlertTriangle, Pause, 
  SkipForward, RotateCcw, Download, FileText, ChevronDown, ChevronUp
} from 'lucide-react';

const ReportSummaryModal = ({ show, onHide, tasks, startTime, endTime }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [exportFormat, setExportFormat] = useState('json');
  const [activeKeys, setActiveKeys] = useState([]);
  
  // Tamamlanan görevleri otomatik olarak açık göster
  useEffect(() => {
    if (show) {
      // Tamamlanmış görevleri otomatik olarak genişlet
      const completedTaskIds = tasks
        .filter(task => task.status === 'completed')
        .map(task => task.id);
      setActiveKeys(completedTaskIds);
    }
  }, [show, tasks]);
  
  // Duruma göre görevleri filtreleme
  const filteredTasks = tasks.filter(task => {
    // Durum filtreleme
    if (statusFilter !== 'all' && task.status !== statusFilter) {
      return false;
    }
    
    // Arama filtreleme
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      return (
        task.name.toLowerCase().includes(searchLower) ||
        task.description.toLowerCase().includes(searchLower) ||
        (task.output && task.output.toLowerCase().includes(searchLower))
      );
    }
    
    return true;
  });
  
  // İstatistikleri hesapla
  const stats = {
    total: tasks.length,
    completed: tasks.filter(task => task.status === 'completed').length,
    failed: tasks.filter(task => task.status === 'failed').length,
    skipped: tasks.filter(task => task.status === 'skipped').length,
    pending: tasks.filter(task => ['pending', 'running', 'paused'].includes(task.status)).length,
    totalDuration: endTime && startTime ? (endTime - startTime) / 1000 : 0
  };
  
  // Durum simgesini alır
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-success" size={18} />;
      case 'failed':
        return <XCircle className="text-danger" size={18} />;
      case 'running':
        return <RotateCcw className="text-primary animate-spin" size={18} />;
      case 'paused':
        return <Pause className="text-warning" size={18} />;
      case 'skipped':
        return <SkipForward className="text-info" size={18} />;
      default:
        return <Clock className="text-secondary" size={18} />;
    }
  };
  
const processTaskOutput = (output, task) => {
    if (!output || output === 'undefined' || output === 'null') return <div className="text-muted">Çıktı yok</div>;
    
    try {
    // Çıktının bir JSON olup olmadığını kontrol et
    let jsonOutput;
    try {
        // Eğer zaten string değilse (object), JSON olarak formatlama
        if (typeof output === 'object') {
        return (
            <div className="output-container">
            <pre className="bg-light p-2 rounded">
                {JSON.stringify(output, null, 2)}
            </pre>
            </div>
        );
        }
        
        // String ise JSON olarak ayrıştırmayı dene
        jsonOutput = JSON.parse(output);
        
        // Başarılı ayrıştırma, formatlayarak göster
        if (typeof jsonOutput === 'object') {
        return (
            <div className="output-container">
            <pre className="bg-light p-2 rounded">
                {JSON.stringify(jsonOutput, null, 2)}
            </pre>
            </div>
        );
        }
    } catch (e) {
        // JSON değil, normal metin olarak devam et
    }
    
    // Tablo verisi olup olmadığını kontrol et (satır ve sütunlar içeren düzenli veri)
    if (typeof output === 'string' && output.includes('|') && output.includes('\n')) {
        const lines = output.trim().split('\n');
        if (lines.length > 1 && lines[0].includes('|') && lines[1].includes('-')) {
        return (
            <div className="table-responsive">
            <table className="table table-sm table-striped">
                <tbody>
                {lines.map((line, idx) => {
                    // Başlık satırını ve ayırıcı satırı atla
                    if (idx === 1 && line.includes('---')) return null;
                    
                    const cells = line.split('|').map(cell => cell.trim());
                    return (
                    <tr key={idx}>
                        {cells.map((cell, cellIdx) => 
                        <td key={cellIdx}>{cell}</td>
                        )}
                    </tr>
                    );
                })}
                </tbody>
            </table>
            </div>
        );
        }
    }
    
    // Eğer çıktı Objeyse veya boş değilse, metin halinde göster
    const displayText = (typeof output === 'object') 
        ? JSON.stringify(output, null, 2) 
        : String(output);
    
    // Satırlarına ayır ve formatlama uygula
    const lines = displayText.split('\n');
    
    // Görsel stillerle zenginleştirilmiş çıktı
    return (
        <div className="output-container">
        {lines.map((line, idx) => {
            // Özel formatlamalar - görev türüne göre önemli bilgileri vurgula
            if (task?.tool === "system_info" || task?.name?.toLowerCase().includes('sistem')) {
            // Sistem bilgisi için vurgulama
            if (line.match(/CPU|RAM|Memory|Disk|Filesystem|System|Network|Usage/i)) {
                return <div key={idx} className="text-primary fw-bold">{line}</div>;
            } 
            else if (line.match(/\b\d+[.,]?\d*\s*%|\b\d+[.,]?\d*\s*(GB|MB|KB)\b/i)) {
                return <div key={idx} className="text-success">{line}</div>;
            }
            }
            else if (task?.tool === "network_manager" || task?.name?.toLowerCase().includes('ağ')) {
            // Ağ bilgisi için vurgulama
            if (line.match(/IP|Port|Network|DNS|Connection/i)) {
                return <div key={idx} className="text-primary fw-bold">{line}</div>;
            }
            }
            
            // Genel formatlamalar
            if (line.match(/warning|caution|attention/i)) {
            return <div key={idx} className="text-warning">{line}</div>;
            }
            else if (line.match(/error|critical|fail|fatal/i)) {
            return <div key={idx} className="text-danger">{line}</div>;
            }
            else if (line.match(/success|ok|completed|done/i)) {
            return <div key={idx} className="text-success">{line}</div>;
            }
            else if (line.match(/^[-]+$|^[=]+$/)) {
            // Ayırıcı çizgiler
            return <hr key={idx} className="my-1" />;
            }
            else if (line.trim().startsWith('#') || line.match(/^[A-Z\s]+:$/)) {
            // Başlık formatında satırlar
            return <div key={idx} className="fw-bold mt-1">{line}</div>;
            }
            else {
            return <div key={idx}>{line || ' '}</div>;
            }
        })}
        </div>
    );
    } catch (error) {
    console.error("Çıktı işleme hatası:", error);
    return <pre className="text-monospace small">{String(output)}</pre>;
    }
};
  
  // Çıktı önizlemesi
  const getOutputPreview = (task) => {
    if (!task.output) return null;
    
    try {
      let output = task.output;
      let preview = '';
      
      // İlk 100 karakteri al
      preview = output.substring(0, 100).trim();
      if (output.length > 100) preview += '...';
      
      // Görev tipine göre önemli bilgileri çıkar
      const keyMetrics = [];
      
      // Sistem bilgisi görevi
      if (task.name.toLowerCase().includes('sistem') || 
          task.description.toLowerCase().includes('cpu') || 
          task.description.toLowerCase().includes('ram')) {
        
        // CPU, RAM, Disk gibi ölçümleri ara
        const cpuMatch = output.match(/CPU.*?(\d+[.,]?\d*\s*%)/i);
        const ramMatch = output.match(/RAM.*?(\d+[.,]?\d*\s*(GB|MB|%|free|used))/i);
        const diskMatch = output.match(/Disk.*?(\d+[.,]?\d*\s*(GB|MB|%))/i);
        
        if (cpuMatch) keyMetrics.push(`CPU: ${cpuMatch[1]}`);
        if (ramMatch) keyMetrics.push(`RAM: ${ramMatch[1]}`);
        if (diskMatch) keyMetrics.push(`Disk: ${diskMatch[1]}`);
      }
      
      // Ağ bilgisi görevi
      else if (task.name.toLowerCase().includes('ağ') || 
               task.description.toLowerCase().includes('network') ||
               task.description.toLowerCase().includes('ping')) {
        
        const pingMatch = output.match(/time=(\d+[.,]?\d*\s*ms)/i);
        const ipMatch = output.match(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/);
        
        if (pingMatch) keyMetrics.push(`Ping: ${pingMatch[1]}`);
        if (ipMatch) keyMetrics.push(`IP: ${ipMatch[0]}`);
      }
      
      // Dosya işlemi görevi
      else if (task.name.toLowerCase().includes('dosya') || 
               task.description.toLowerCase().includes('file')) {
        
        const countMatch = output.match(/(\d+)\s+files/i);
        const sizeMatch = output.match(/(\d+[.,]?\d*\s*(GB|MB|KB|bytes))/i);
        
        if (countMatch) keyMetrics.push(`${countMatch[1]} dosya`);
        if (sizeMatch) keyMetrics.push(`${sizeMatch[1]}`);
      }
      
      // Önemli metrikler varsa onları göster
      if (keyMetrics.length > 0) {
        return (
          <div className="mt-1">
            {keyMetrics.map((metric, idx) => (
              <Badge 
                key={idx} 
                bg="info" 
                className="me-1" 
                style={{ fontSize: '0.75rem' }}
              >
                {metric}
              </Badge>
            ))}
          </div>
        );
      }
      
      // Başka türlü çıktı önizlemesi
      return <div className="small text-muted mt-1">{preview}</div>;
      
    } catch (error) {
      return null;
    }
  };
  
  // Accordionu aç/kapat
  const handleAccordionToggle = (taskId) => {
    setActiveKeys(prevKeys => {
      if (prevKeys.includes(taskId)) {
        return prevKeys.filter(key => key !== taskId);
      } else {
        return [...prevKeys, taskId];
      }
    });
  };
  
  // Tüm görevleri aç/kapat
  const toggleAllTasks = (open) => {
    if (open) {
      setActiveKeys(filteredTasks.map(task => task.id));
    } else {
      setActiveKeys([]);
    }
  };
  
  // Raporu dışa aktarma
  const exportReport = () => {
    // Raporun metin/JSON versiyonunu oluştur
    let content = '';
    let filename = `task-report-${new Date().toISOString().slice(0, 10)}`;
    
    if (exportFormat === 'json') {
      // JSON formatında rapor oluştur
      const reportData = {
        summary: {
          totalTasks: stats.total,
          completedTasks: stats.completed,
          failedTasks: stats.failed,
          skippedTasks: stats.skipped,
          pendingTasks: stats.pending,
          totalDuration: stats.totalDuration,
          startTime: startTime ? new Date(startTime).toISOString() : null,
          endTime: endTime ? new Date(endTime).toISOString() : null
        },
        tasks: tasks.map(task => ({
          id: task.id,
          name: task.name,
          description: task.description,
          status: task.status,
          command: task.command,
          output: task.output,
          startTime: task.startTime ? new Date(task.startTime).toISOString() : null,
          endTime: task.endTime ? new Date(task.endTime).toISOString() : null,
          duration: task.startTime && task.endTime ? (task.endTime - task.startTime) / 1000 : null
        }))
      };
      
      content = JSON.stringify(reportData, null, 2);
      filename += '.json';
    } else {
      // Metin formatında rapor oluştur
      // Başlık
      content += '===== GÖREV RAPORU =====\n\n';
      
      // Özet bilgileri
      content += `Oluşturma Tarihi: ${new Date().toLocaleString()}\n`;
      content += `Çalışma Başlangıç: ${startTime ? new Date(startTime).toLocaleString() : 'Bilinmiyor'}\n`;
      content += `Çalışma Bitiş: ${endTime ? new Date(endTime).toLocaleString() : 'Bilinmiyor'}\n`;
      content += `Toplam Süre: ${stats.totalDuration.toFixed(2)} saniye\n\n`;
      
      content += `Toplam Görev: ${stats.total}\n`;
      content += `Tamamlanan: ${stats.completed}\n`;
      content += `Başarısız: ${stats.failed}\n`;
      content += `Atlanan: ${stats.skipped}\n`;
      content += `Bekleyen: ${stats.pending}\n\n`;
      
      content += '===== GÖREV DETAYLARI =====\n\n';
      
      // Görev detayları
      tasks.forEach((task, index) => {
        content += `Görev ${index + 1}: ${task.name}\n`;
        content += `Durum: ${task.status}\n`;
        content += `Açıklama: ${task.description}\n`;
        content += `Komut: ${task.command}\n`;
        
        if (task.startTime) {
          content += `Başlangıç: ${new Date(task.startTime).toLocaleString()}\n`;
          
          if (task.endTime) {
            content += `Bitiş: ${new Date(task.endTime).toLocaleString()}\n`;
            content += `Süre: ${((task.endTime - task.startTime) / 1000).toFixed(2)} saniye\n`;
          }
        }
        
        content += `Çıktı:\n${task.output || 'Çıktı yok'}\n\n`;
        content += '------------------------\n\n';
      });
      
      filename += '.txt';
    }
    
    // Dosyayı oluştur ve indir
    const blob = new Blob([content], { type: exportFormat === 'json' ? 'application/json' : 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  return (
    <Modal show={show} onHide={onHide} size="xl">
      <Modal.Header closeButton>
        <Modal.Title>
          <FileText className="me-2" size={20} />
          Görev Raporu
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {/* Özet ve İstatistikler */}
        <Card className="mb-4">
          <Card.Header className="bg-light">
            <h6 className="mb-0">Rapor Özeti</h6>
          </Card.Header>
          <Card.Body>
            <div className="row">
              {/* Durum İstatistikleri */}
              <div className="col-md-7">
                <div className="mb-3">
                  <h6>Görev Durumları</h6>
                  
                  {/* İlerleme Çubuğu */}
                  <ProgressBar className="mb-2" style={{ height: '25px' }}>
                    <ProgressBar 
                      variant="success" 
                      now={(stats.completed / stats.total) * 100} 
                      key={1} 
                      label={`${stats.completed}`}
                    />
                    <ProgressBar 
                      variant="danger" 
                      now={(stats.failed / stats.total) * 100} 
                      key={2} 
                      label={`${stats.failed}`}
                    />
                    <ProgressBar 
                      variant="warning" 
                      now={(stats.skipped / stats.total) * 100} 
                      key={3} 
                      label={`${stats.skipped}`}
                    />
                    <ProgressBar 
                      variant="secondary" 
                      now={(stats.pending / stats.total) * 100} 
                      key={4} 
                      label={`${stats.pending}`}
                    />
                  </ProgressBar>
                  
                  <div className="d-flex flex-wrap justify-content-between">
                    <div className="d-flex align-items-center me-3">
                      <span className="badge bg-success me-1">&nbsp;</span>
                      <small>Tamamlanan: {stats.completed}</small>
                    </div>
                    <div className="d-flex align-items-center me-3">
                      <span className="badge bg-danger me-1">&nbsp;</span>
                      <small>Başarısız: {stats.failed}</small>
                    </div>
                    <div className="d-flex align-items-center me-3">
                      <span className="badge bg-warning me-1">&nbsp;</span>
                      <small>Atlanan: {stats.skipped}</small>
                    </div>
                    <div className="d-flex align-items-center">
                      <span className="badge bg-secondary me-1">&nbsp;</span>
                      <small>Bekleyen: {stats.pending}</small>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Çalışma Bilgileri */}
              <div className="col-md-5">
                <h6>Çalışma Bilgileri</h6>
                <table className="table table-sm">
                  <tbody>
                    <tr>
                      <td>Toplam Görev</td>
                      <td className="text-end">{stats.total}</td>
                    </tr>
                    <tr>
                      <td>Başlangıç</td>
                      <td className="text-end">
                        {startTime 
                          ? new Date(startTime).toLocaleString() 
                          : '-'}
                      </td>
                    </tr>
                    <tr>
                      <td>Bitiş</td>
                      <td className="text-end">
                        {endTime 
                          ? new Date(endTime).toLocaleString() 
                          : '-'}
                      </td>
                    </tr>
                    <tr>
                      <td>Toplam Süre</td>
                      <td className="text-end">
                        {stats.totalDuration.toFixed(2)} saniye
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </Card.Body>
        </Card>
        
        {/* Arama, Filtreleme ve Dışa Aktarma */}
        <div className="d-flex justify-content-between mb-3 flex-wrap">
          <div className="d-flex gap-2 flex-grow-1 me-2 mb-2">
            <Form.Control
              type="text"
              placeholder="Görevlerde ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-grow-1"
              style={{ maxWidth: '300px' }}
            />
            
            <Form.Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: 'auto' }}
            >
              <option value="all">Tüm Durumlar</option>
              <option value="completed">Tamamlanan</option>
              <option value="failed">Başarısız</option>
              <option value="skipped">Atlanan</option>
              <option value="pending">Bekleyen</option>
            </Form.Select>
            
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => toggleAllTasks(true)}
              className="ms-2"
            >
              <ChevronDown size={16} className="me-1" /> Tümünü Aç
            </Button>
            
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => toggleAllTasks(false)}
              className="ms-1"
            >
              <ChevronUp size={16} className="me-1" /> Tümünü Kapat
            </Button>
          </div>
          
          <div className="d-flex gap-2 mb-2">
            <Form.Select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              style={{ width: 'auto' }}
            >
              <option value="json">JSON</option>
              <option value="text">Metin (.txt)</option>
            </Form.Select>
            
            <Button 
              variant="primary" 
              onClick={exportReport}
              disabled={tasks.length === 0}
            >
              <Download size={16} className="me-2" />
              Raporu İndir
            </Button>
          </div>
        </div>
        
        {/* Görev Sonuçları */}
        <Card>
          <Card.Header className="bg-light">
            <h6 className="mb-0">
              Görev Sonuçları 
              <Badge bg="secondary" className="ms-2">
                {filteredTasks.length}/{tasks.length}
              </Badge>
            </h6>
          </Card.Header>
          
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {filteredTasks.length > 0 ? (
              filteredTasks.map((task) => (
                <div 
                  key={task.id} 
                  className="border-bottom p-3"
                >
                  <div 
                    className="d-flex justify-content-between align-items-start cursor-pointer"
                    onClick={() => handleAccordionToggle(task.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="d-flex align-items-start">
                      <div className="me-2 mt-1">
                        {getStatusIcon(task.status)}
                      </div>
                      
                      <div>
                        <h6 className="mb-1 d-flex align-items-center">
                          {task.name}
                          <Badge 
                            bg={
                              task.status === 'completed' ? 'success' :
                              task.status === 'failed' ? 'danger' :
                              task.status === 'skipped' ? 'warning' :
                              'secondary'
                            }
                            className="ms-2"
                          >
                            {task.status}
                          </Badge>
                        </h6>
                        
                        <div className="text-muted small mb-1">{task.description}</div>
                        <div className="bg-light rounded p-1 small mb-1">
                          <code>{task.command}</code>
                        </div>
                        
                        {/* Çıktı önizlemesi */}
                        {getOutputPreview(task)}
                      </div>
                    </div>
                    
                    <Button 
                      variant="light" 
                      size="sm" 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAccordionToggle(task.id);
                      }}
                    >
                      {activeKeys.includes(task.id) ? 
                        <ChevronUp size={16} /> : 
                        <ChevronDown size={16} />
                      }
                    </Button>
                  </div>
                  
                  {/* Görev detayları ve çıktısı */}
                  {activeKeys.includes(task.id) && (
                    <div className="mt-3">
                      <hr />
                      
                      {/* Çalışma zamanı bilgileri */}
                      {task.startTime && (
                        <div className="d-flex mb-2 text-muted small">
                          <div className="me-3">
                            <strong>Başlangıç:</strong> {new Date(task.startTime).toLocaleString()}
                          </div>
                          
                          {task.endTime && (
                            <>
                              <div className="me-3">
                                <strong>Bitiş:</strong> {new Date(task.endTime).toLocaleString()}
                              </div>
                              <div>
                                <strong>Süre:</strong> {((task.endTime - task.startTime) / 1000).toFixed(2)} saniye
                              </div>
                            </>
                          )}
                        </div>
                      )}
                      
                      {/* Detaylı çıktı */}
                      <Card className="output-card mt-2">
                        <Card.Header className="py-2 px-3 bg-light">
                          <strong>Çıktı</strong>
                        </Card.Header>
                        <Card.Body 
                          className="p-3" 
                          style={{ 
                            maxHeight: '300px', 
                            overflowY: 'auto', 
                            fontSize: '0.875rem'
                          }}
                        >
                          {processTaskOutput(task.output, task)}
                        </Card.Body>
                      </Card>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-muted">
                <AlertTriangle size={24} className="mb-2" />
                <p className="mb-0">Filtreleme kriterlerine uygun görev bulunamadı.</p>
              </div>
            )}
          </div>
        </Card>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>Kapat</Button>
      </Modal.Footer>
    </Modal>
  );
};

export default ReportSummaryModal;