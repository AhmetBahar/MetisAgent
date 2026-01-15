// src/pages/Editor.js
import React, { useState, useEffect, useRef } from 'react';
import { Editor as MonacoEditor } from '@monaco-editor/react';
import { EditorAPI } from '../services/api';
import { 
  Save, FolderOpen, Play, Share2, Check, X, AlertTriangle,
  Code, Eye, ArrowLeftRight, RefreshCw
} from 'lucide-react';

const Editor = () => {
  const [files, setFiles] = useState([]);
  const [currentFile, setCurrentFile] = useState(null);
  const [editorContent, setEditorContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState([]);
  const editorRef = useRef(null);
  
  // LLM değişiklik önizleme state'leri
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [diffViewMode, setDiffViewMode] = useState(false);
  
  // Fetch file list on component mount
  useEffect(() => {
    fetchFiles();
    fetchTemplates();
  }, []);
  
  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await EditorAPI.getFiles();
      setFiles(response.files || []);
    } catch (error) {
      console.error('Error fetching files:', error);
      // Demo mock data
      setFiles([
        { name: 'example.py', path: '/example.py' },
        { name: 'config.json', path: '/config.json' },
        { name: 'README.md', path: '/README.md' }
      ]);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchTemplates = async () => {
    try {
      const response = await EditorAPI.getTemplates();
      setTemplates(response.templates || []);
    } catch (error) {
      console.error('Error fetching templates:', error);
      // Demo mock data
      setTemplates([
        { id: 'add-function', name: 'Add Function', description: 'Adds a new function to the current code' },
        { id: 'fix-error', name: 'Fix Error', description: 'Attempts to fix common errors in the code' },
        { id: 'refactor-code', name: 'Refactor Code', description: 'Improves code structure and readability' }
      ]);
    }
  };
  
  const loadFile = async (file) => {
    try {
      setLoading(true);
      const response = await EditorAPI.getFileContent(file.path);
      setEditorContent(response.content);
      setCurrentFile(file);
      // Önizleme modu aktifse kapat
      if (showPreview) {
        setShowPreview(false);
        setPreviewData(null);
      }
    } catch (error) {
      console.error('Error loading file:', error);
      // Demo mock data
      const mockContent = getMockContent(file.name);
      setEditorContent(mockContent);
      setCurrentFile(file);
    } finally {
      setLoading(false);
    }
  };
  
  const getMockContent = (fileName) => {
    if (fileName.endsWith('.py')) {
      return '# Example Python File\n\ndef hello_world():\n    print("Hello, world!")\n\nif __name__ == "__main__":\n    hello_world()';
    } else if (fileName.endsWith('.json')) {
      return '{\n  "name": "Metis Agent",\n  "version": "1.0.0",\n  "description": "OS functions accessible via API"\n}';
    } else {
      return '# Metis Agent\n\nA tool for system automation and management.\n\n## Features\n\n- File Management\n- User Management\n- Network Management';
    }
  };
  
  const saveFile = async () => {
    if (!currentFile) return;
    
    try {
      setLoading(true);
      await EditorAPI.saveFile(currentFile.path, editorContent);
      alert('File saved successfully!');
    } catch (error) {
      console.error('Error saving file:', error);
      alert('Error saving file. Check console for details.');
    } finally {
      setLoading(false);
    }
  };
  
  // Preview LLM changes before applying
  const previewTemplate = async (templateId) => {
    if (!currentFile) return;
    
    try {
      setPreviewLoading(true);
      setShowPreview(true);
      
      const response = await EditorAPI.previewChanges(currentFile.path, templateId, editorContent);
      
      setPreviewData({
        original: response.original,
        modified: response.modified,
        changes: response.changes,
        templateName: response.templateName,
        templateDescription: response.templateDescription,
        templateId: templateId
      });
      
    } catch (error) {
      console.error('Error previewing template:', error);
      alert('Error previewing template changes. Check console for details.');
      setShowPreview(false);
    } finally {
      setPreviewLoading(false);
    }
  };
  
  // Apply changes after preview
  const applyPreviewedChanges = () => {
    if (previewData) {
      setEditorContent(previewData.modified);
      setShowPreview(false);
      setPreviewData(null);
    }
  };
  
  // Cancel preview
  const cancelPreview = () => {
    setShowPreview(false);
    setPreviewData(null);
    setDiffViewMode(false);
  };
  
  // Handle editor instance
  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Setup diff editor if needed
    if (showPreview && previewData && diffViewMode) {
      setupDiffEditor(monaco);
    }
  };
  
  // Setup diff editor
  const setupDiffEditor = (monaco) => {
    if (!editorRef.current || !previewData) return;
    
    const diffEditor = monaco.editor.createDiffEditor(editorRef.current.getContainerDomNode(), {
      originalEditable: false,
      readOnly: true
    });
    
    const originalModel = monaco.editor.createModel(
      previewData.original,
      getLanguage(currentFile?.name)
    );
    
    const modifiedModel = monaco.editor.createModel(
      previewData.modified,
      getLanguage(currentFile?.name)
    );
    
    diffEditor.setModel({
      original: originalModel,
      modified: modifiedModel
    });
  };
  
  // Get language based on file extension
  const getLanguage = (filename) => {
    if (!filename) return 'plaintext';
    if (filename.endsWith('.py')) return 'python';
    if (filename.endsWith('.js')) return 'javascript';
    if (filename.endsWith('.html')) return 'html';
    if (filename.endsWith('.css')) return 'css';
    if (filename.endsWith('.json')) return 'json';
    if (filename.endsWith('.md')) return 'markdown';
    return 'plaintext';
  };
  
  // Get change type icon
  const getChangeTypeIcon = (type) => {
    switch (type) {
      case 'add':
        return <span className="text-green-500">+</span>;
      case 'delete':
        return <span className="text-red-500">-</span>;
      case 'replace':
        return <span className="text-blue-500">↔</span>;
      case 'search_replace':
        return <span className="text-purple-500">⇄</span>;
      default:
        return <span>•</span>;
    }
  };
  
  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b p-2 flex justify-between items-center">
        <div className="flex items-center">
          <h2 className="text-lg font-semibold">
            {currentFile ? currentFile.name : 'Editor'}
          </h2>
          {currentFile && <span className="ml-2 text-gray-500 text-sm">{currentFile.path}</span>}
        </div>
        <div className="flex space-x-2">
          {!showPreview ? (
            <>
              <button 
                className="p-2 bg-blue-500 text-white rounded flex items-center"
                onClick={saveFile}
                disabled={!currentFile || loading}
              >
                <Save size={16} className="mr-1" />
                Save
              </button>
            </>
          ) : (
            <>
              <button 
                className="p-2 bg-green-500 text-white rounded flex items-center"
                onClick={applyPreviewedChanges}
                disabled={!previewData || previewLoading}
              >
                <Check size={16} className="mr-1" />
                Apply Changes
              </button>
              <button 
                className="p-2 bg-gray-500 text-white rounded flex items-center"
                onClick={cancelPreview}
                disabled={previewLoading}
              >
                <X size={16} className="mr-1" />
                Cancel
              </button>
              <button 
                className={`p-2 ${diffViewMode ? 'bg-purple-500' : 'bg-gray-200'} text-${diffViewMode ? 'white' : 'gray-700'} rounded flex items-center`}
                onClick={() => setDiffViewMode(!diffViewMode)}
                disabled={previewLoading}
              >
                <ArrowLeftRight size={16} className="mr-1" />
                {diffViewMode ? 'Normal View' : 'Diff View'}
              </button>
            </>
          )}
        </div>
      </div>
      
      <div className="flex-1 flex">
        {/* File Explorer Sidebar */}
        <div className="w-64 bg-gray-100 border-r overflow-y-auto">
          <div className="p-3 border-b bg-gray-200">
            <h3 className="font-medium">Files</h3>
          </div>
          <div className="p-2">
            {loading && files.length === 0 ? (
              <p className="text-sm text-gray-500">Loading files...</p>
            ) : (
              <ul>
                {files.map((file, index) => (
                  <li key={index} className="mb-1">
                    <button
                      className={`w-full text-left p-2 rounded text-sm ${
                        currentFile && currentFile.path === file.path
                          ? 'bg-blue-100 text-blue-700'
                          : 'hover:bg-gray-200'
                      }`}
                      onClick={() => loadFile(file)}
                    >
                      {file.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          {/* Templates Section */}
          <div className="p-3 border-b bg-gray-200 mt-4">
            <h3 className="font-medium">LLM Templates</h3>
          </div>
          <div className="p-2">
            {templates.length === 0 ? (
              <p className="text-sm text-gray-500">No templates available</p>
            ) : (
              <ul>
                {templates.map((template, index) => (
                  <li key={index} className="mb-1">
                    <button
                      className="w-full text-left p-2 rounded text-sm hover:bg-gray-200"
                      onClick={() => previewTemplate(template.id)}
                      disabled={!currentFile || showPreview || loading}
                    >
                      {template.name}
                      {template.description && (
                        <p className="text-xs text-gray-500">{template.description}</p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        
        {/* Editor Area */}
        <div className="flex-1">
          {!currentFile ? (
            <div className="h-full flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <FolderOpen size={48} className="mx-auto text-gray-400 mb-4" />
                <h3 className="text-xl font-medium text-gray-700">No File Selected</h3>
                <p className="text-gray-500 mt-2">Select a file from the sidebar to start editing</p>
              </div>
            </div>
          ) : showPreview ? (
            <div className="h-full flex flex-col">
              {previewLoading ? (
                <div className="h-full flex items-center justify-center">
                  <RefreshCw size={48} className="animate-spin text-blue-500" />
                </div>
              ) : (
                <>
                  {/* Preview header */}
                  <div className="bg-gray-100 p-3 border-b">
                    <h3 className="font-medium">{previewData?.templateName || 'Preview Changes'}</h3>
                    {previewData?.templateDescription && (
                      <p className="text-sm text-gray-600 mt-1">{previewData.templateDescription}</p>
                    )}
                  </div>
                  
                  {/* Diff View or Regular View with Changes List */}
                  {diffViewMode ? (
                    // Diff Editor View
                    <div className="flex-1">
                      <MonacoEditor
                        height="100%"
                        language={getLanguage(currentFile.name)}
                        value={previewData?.modified || ''}
                        theme="vs-dark"
                        options={{
                          readOnly: true,
                          minimap: { enabled: true },
                          scrollBeyondLastLine: false,
                          fontSize: 14,
                          wordWrap: 'on',
                        }}
                        onMount={handleEditorDidMount}
                      />
                    </div>
                  ) : (
                    // Regular View with Changes List
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-3">
                      {/* Changes List */}
                      <div className="border-r overflow-y-auto">
                        <div className="p-3 border-b bg-gray-100">
                          <h4 className="font-medium">Changes to Apply</h4>
                        </div>
                        <ul className="divide-y">
                          {previewData?.changes.map((change, index) => (
                            <li key={index} className="p-3 hover:bg-gray-50">
                              <div className="flex items-start">
                                <div className="mr-2 mt-1">
                                  {getChangeTypeIcon(change.type)}
                                </div>
                                <div>
                                  <p className="text-sm font-medium">{change.description}</p>
                                  {change.type === 'search_replace' && (
                                    <div className="mt-1 text-xs">
                                      <p className="text-red-600">- {change.search}</p>
                                      <p className="text-green-600">+ {change.replace}</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                      
                      {/* Modified Code Preview */}
                      <div className="col-span-2">
                        <MonacoEditor
                          height="100%"
                          language={getLanguage(currentFile.name)}
                          value={previewData?.modified || ''}
                          theme="vs-dark"
                          options={{
                            readOnly: true,
                            minimap: { enabled: true },
                            scrollBeyondLastLine: false,
                            fontSize: 14,
                            wordWrap: 'on',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <MonacoEditor
              height="100%"
              language={getLanguage(currentFile.name)}
              value={editorContent}
              onChange={setEditorContent}
              theme="vs-dark"
              options={{
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                fontSize: 14,
                wordWrap: 'on',
                automaticLayout: true,
              }}
              onMount={handleEditorDidMount}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Editor;