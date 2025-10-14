'use client'

import { useState, useRef, useEffect } from 'react'

export interface Message {
  id: number
  sender: 'user' | 'bot'
  content: string
  timestamp: Date
}

export interface Citation {
  page: number
  text: string
  filename?: string
  score: number
  images?: string[]
}

export interface WebResult {
  title: string
  link: string
  snippet: string
  displayLink: string
}

export default function Home() {
  // State management
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: 'bot',
      content: 'Hello! Upload a PDF and ask me questions about it using text or voice.',
      timestamp: new Date()
    }
  ])
  
  const [citations, setCitations] = useState<Citation[]>([])
  const [webResults, setWebResults] = useState<WebResult[]>([])
  const [currentTranscription, setCurrentTranscription] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messageInput, setMessageInput] = useState('')
  const [uploadStatus, setUploadStatus] = useState('')
  const [uploadStatusClass, setUploadStatusClass] = useState('')
  const [currentDocument, setCurrentDocument] = useState<string>('')
  
  // Voice recognition state
  const [isListening, setIsListening] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('Ready')
  const [statusClass, setStatusClass] = useState('')
  
  // Message ID counter to ensure unique IDs
  const messageIdCounter = useRef(1000)
  
  // Refs
  const websocketRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const lastProcessedTranscriptRef = useRef<string>('')
  const processingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isProcessingRef = useRef<boolean>(false)

  // Initialize Deepgram WebSocket connection
  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (websocketRef.current) {
        websocketRef.current.close()
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Helper functions
  const resetVoiceControls = () => {
    setIsListening(false)
    setVoiceStatus('Ready')
    setStatusClass('')
    setCurrentTranscription('')
    lastProcessedTranscriptRef.current = ''
    isProcessingRef.current = false
    
    // Clear any pending timeouts
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current)
      processingTimeoutRef.current = null
    }
  }

  const startListening = async () => {
    try {
      // Check if Web Speech API is supported
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        setVoiceStatus('Speech recognition not supported in this browser')
        setStatusClass('error')
        return
      }

      // Create speech recognition instance
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      const recognition = new SpeechRecognition()
      
      // Configure speech recognition
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      recognition.maxAlternatives = 1

      setIsListening(true)
      setVoiceStatus('Listening...')
      setStatusClass('listening')

      recognition.onstart = () => {
        console.log('Speech recognition started')
        setVoiceStatus('Listening... Speak now!')
      }

      recognition.onresult = (event: any) => {
        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          const confidence = event.results[i][0].confidence

          if (event.results[i].isFinal) {
            finalTranscript += transcript
            console.log('Final transcript:', transcript)
          } else {
            interimTranscript += transcript
          }
        }

        // Update current transcription display
        if (interimTranscript) {
          setCurrentTranscription(interimTranscript)
          setVoiceStatus('Listening... (processing)')
        }

        // Handle final transcript with robust duplicate prevention
        if (finalTranscript.trim()) {
          const trimmedTranscript = finalTranscript.trim()
          
          // Prevent duplicate messages with multiple checks
          if (trimmedTranscript !== lastProcessedTranscriptRef.current && !isProcessingRef.current) {
            console.log('Adding final message:', trimmedTranscript)
            
            // Set processing flag immediately to prevent duplicates
            isProcessingRef.current = true
            lastProcessedTranscriptRef.current = trimmedTranscript
            
            const messageId = addMessage('user', trimmedTranscript)
            setCurrentTranscription('')
            setVoiceStatus('Processing your message...')
            
            // Clear any existing timeout to prevent multiple sends
            if (processingTimeoutRef.current) {
              clearTimeout(processingTimeoutRef.current)
            }
            
            // Auto-send the message after final transcription
            processingTimeoutRef.current = setTimeout(() => {
              sendMessage(trimmedTranscript)
              processingTimeoutRef.current = null
              // Reset processing flag after a delay to allow for new messages
              setTimeout(() => {
                isProcessingRef.current = false
              }, 2000)
            }, 500)
          } else {
            console.log('Duplicate transcript ignored:', trimmedTranscript)
          }
        }
      }

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        let errorMessage = 'Speech recognition error'
        
        switch (event.error) {
          case 'no-speech':
            errorMessage = 'No speech detected. Try speaking louder.'
            break
          case 'audio-capture':
            errorMessage = 'Audio capture failed. Check your microphone.'
            break
          case 'not-allowed':
            errorMessage = 'Microphone access denied'
            break
          case 'network':
            errorMessage = 'Network error occurred'
            break
          default:
            errorMessage = `Speech recognition error: ${event.error}`
        }
        
        setVoiceStatus(errorMessage)
        setStatusClass('error')
        resetVoiceControls()
      }

      recognition.onend = () => {
        console.log('Speech recognition ended')
        if (isListening) {
          setVoiceStatus('Stopped listening')
          resetVoiceControls()
        }
      }

      // Store recognition instance for cleanup
      websocketRef.current = recognition as any

      // Start recognition
      recognition.start()

    } catch (error: any) {
      console.error('Error starting voice recognition:', error)
      setVoiceStatus('Failed to start voice recognition')
      setStatusClass('error')
      resetVoiceControls()
    }
  }

  const stopListening = () => {
    if (websocketRef.current) {
      // Stop speech recognition
      try {
        (websocketRef.current as any).stop()
      } catch (error) {
        console.log('Error stopping speech recognition:', error)
      }
      websocketRef.current = null
    }
    
    resetVoiceControls()
  }

  const addMessage = (sender: 'user' | 'bot', content: string): number => {
    messageIdCounter.current += 1
    const newMessage: Message = {
      id: messageIdCounter.current,
      sender,
      content,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newMessage])
    return newMessage.id
  }

  const updateMessage = (messageId: number, content: string) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, content } : msg
      )
    )
  }

  const sendMessage = async (message: string) => {
    if (!message.trim()) return

    addMessage('user', message)
    const loadingId = addMessage('bot', 'Thinking...')
    setIsLoading(true)
    
    try {
      const formData = new FormData()
      formData.append('query', message)
      formData.append('include_web', 'true')
      
      const response = await fetch('http://localhost:8000/ask-hybrid/', {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      
      if (result.error) {
        throw new Error(result.error)
      }
      
      updateMessage(loadingId, result.answer)
      
      // Filter citations to only show from current document and deduplicate by page
      const filteredCitations = (result.rag_citations || [])
        .filter((citation: Citation) => {
          // Only show citations from current document if we have one
          if (currentDocument) {
            return citation.filename === currentDocument
          }
          return true
        })
        .filter((citation: Citation, index: number, self: Citation[]) => 
          // Deduplicate by page number within the same document
          index === self.findIndex((c) => c.page === citation.page && c.filename === citation.filename)
        )
        .slice(0, 5) // Limit to maximum 5 citations
      
      setCitations(filteredCitations)
      setWebResults(result.web_results || [])
      
    } catch (error) {
      updateMessage(loadingId, `Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendMessage = () => {
    if (messageInput.trim()) {
      sendMessage(messageInput.trim())
      setMessageInput('')
    }
  }

  const handleUseVoice = () => {
    if (currentTranscription.trim()) {
      sendMessage(currentTranscription.trim())
      setCurrentTranscription('')
    } else {
      alert('No voice transcription available. Please use voice input first.')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleFileUpload = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setUploadStatus('Please select a PDF file')
      setUploadStatusClass('error')
      return
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('Please select a PDF file')
      setUploadStatusClass('error')
      return
    }

    setUploadStatus('Uploading...')
    setUploadStatusClass('')

    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const uploadResponse = await fetch('http://localhost:8000/upload-pdf/', {
        method: 'POST',
        body: formData
      })
      
      const uploadResult = await uploadResponse.json()
      
      if (uploadResult.error) {
        throw new Error(uploadResult.error)
      }

      setUploadStatus('Indexing...')
      
      const indexFormData = new FormData()
      indexFormData.append('file_path', uploadResult.path)
      
      const indexResponse = await fetch('http://localhost:8000/index-pdf/', {
        method: 'POST',
        body: indexFormData
      })
      
      const indexResult = await indexResponse.json()
      
      if (indexResult.error) {
        throw new Error(indexResult.error)
      }

      setUploadStatus(`Indexed successfully! (${indexResult.chunks_stored} chunks)`)
      setUploadStatusClass('')
      
      // Set current document for filtering citations
      setCurrentDocument(file.name)
      
      addMessage('bot', `PDF "${file.name}" uploaded and indexed successfully! You can now ask questions about it.`)
      
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setUploadStatus(`Error: ${errorMessage}`)
      setUploadStatusClass('error')
    }
  }

  return (
    <div className="main-container">
      <div className="sections-container">
        <div className="section voice-section">
          <h2>Voice Transcription</h2>
          <div className="voice-controls">
            <button 
              onClick={startListening}
              disabled={isListening}
              className="btn"
            >
              Start Listening
            </button>
            <button 
              onClick={stopListening}
              disabled={!isListening}
              className="btn btn-secondary"
            >
              Stop Listening
            </button>
            <span className={`voice-status ${statusClass}`}>
              {voiceStatus}
            </span>
          </div>
          <div className="transcription-box">
            {currentTranscription ? (
              <p><strong>Transcription:</strong> {currentTranscription}</p>
            ) : (
              <p>Voice transcription will appear here...</p>
            )}
          </div>
        </div>

        <div className="section chat-section">
          <h2>AI Chatbot</h2>

        <div className="upload-section">
          <input 
            type="file" 
            ref={fileInputRef}
            accept=".pdf"
            style={{ flex: 1, minWidth: '150px' }}
          />
          <button 
            onClick={handleFileUpload}
            className="btn"
            disabled={isLoading}
          >
            Upload & Index PDF
          </button>
          {uploadStatus && (
            <span className={`upload-status ${uploadStatusClass}`}>
              {uploadStatus}
            </span>
          )}
        </div>

        <div className="chat-messages">
          {messages.map((message) => (
            <div 
              key={message.id} 
              className={`message ${message.sender}-message`}
            >
              <strong>{message.sender === 'user' ? 'You' : 'Bot'}:</strong> {message.content}
            </div>
          ))}
          {isLoading && (
            <div className="message bot-message">
              <strong>Bot:</strong> <span className="loading"></span> Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        
        <div className="chat-input">
          <input
            type="text"
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question or use voice..."
            className="message-input"
            disabled={isLoading}
          />
          <button 
            onClick={handleSendMessage}
            disabled={isLoading || !messageInput.trim()}
            className="btn"
          >
            Send
          </button>
          <button 
            onClick={handleUseVoice}
            disabled={isLoading || !currentTranscription.trim()}
            className="btn btn-secondary"
          >
            Use Voice
          </button>
        </div>
        </div>

        <div className="section citations-section">
          <h2>References & Citations</h2>
          <div className="citations-container">
            {citations.length > 0 && (
              <div>
                <h3 style={{ fontSize: '14px', marginBottom: '8px', color: '#2c3e50' }}>
                  Document Citations ({citations.length})
                  {currentDocument && (
                    <div style={{ 
                      fontSize: '11px', 
                      color: '#7f8c8d', 
                      fontWeight: 'normal',
                      marginTop: '2px'
                    }}>
                      From: {currentDocument}
                    </div>
                  )}
                </h3>
                {citations.map((citation, index) => (
                  <div key={`${citation.filename}-${citation.page}-${index}`} className="citation-item">
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <h4 style={{ fontSize: '13px', color: '#3498db', margin: 0 }}>
                        {citation.filename || 'Unknown Document'}
                      </h4>
                      <span style={{ 
                        fontSize: '11px', 
                        background: '#f39c12', 
                        color: 'white', 
                        padding: '2px 6px', 
                        borderRadius: '3px' 
                      }}>
                        Page {citation.page}
                      </span>
                    </div>
                    
                    {citation.filename && (
                      <div style={{ textAlign: 'center' }}>
                        <img
                          className="pdf-page-image"
                          src={`http://localhost:8000/pdf-page-highlighted/${citation.filename}/${citation.page}?highlight_text=${encodeURIComponent(citation.text.substring(0, 150))}`}
                          alt={`Page ${citation.page} from ${citation.filename} with highlighted context`}
                          style={{
                            width: '100%',
                            maxHeight: '200px',
                            border: '2px solid #f39c12',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            objectFit: 'contain'
                          }}
                          onError={(e) => {
                            const target = e.currentTarget as HTMLImageElement
                            // Fallback to regular PDF image if highlighting fails
                            target.src = `http://localhost:8000/pdf-page-image/${citation.filename}/${citation.page}`
                            target.style.border = '2px solid #3498db'
                          }}
                          onClick={() => {
                            window.open(`http://localhost:8000/pdf-page-highlighted/${citation.filename}/${citation.page}?highlight_text=${encodeURIComponent(citation.text.substring(0, 150))}`, '_blank')
                          }}
                        />
                        <p style={{ 
                          fontSize: '10px', 
                          color: '#7f8c8d', 
                          marginTop: '4px',
                          fontStyle: 'italic'
                        }}>
                          Click to view full size • Relevance: {(citation.score * 100).toFixed(1)}% • Highlighted
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {webResults.length > 0 && (
              <div style={{ marginTop: '15px', borderTop: '1px solid #ddd', paddingTop: '10px' }}>
                <h3 style={{ fontSize: '14px', marginBottom: '8px', color: '#2c3e50' }}>Web Search Results ({webResults.length})</h3>
                {webResults.slice(0, 3).map((result, index) => (
                  <div key={index} className="citation-item" style={{ borderLeft: '3px solid #27ae60' }}>
                    <h4 style={{ fontSize: '13px', marginBottom: '4px' }}>
                      <a 
                        href={result.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ 
                          color: '#27ae60', 
                          textDecoration: 'none',
                          fontWeight: 'bold'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.textDecoration = 'underline'}
                        onMouseOut={(e) => e.currentTarget.style.textDecoration = 'none'}
                      >
                        {result.title}
                      </a>
                    </h4>
                    <div style={{ 
                      fontSize: '12px',
                      lineHeight: '1.4',
                      marginBottom: '6px',
                      color: '#555'
                    }}>
                      {result.snippet}
                    </div>
                    <div style={{ 
                      fontSize: '10px', 
                      color: '#7f8c8d',
                      marginTop: '4px'
                    }}>
                      Source: {new URL(result.link).hostname}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {citations.length === 0 && webResults.length === 0 && (
              <p>Citations and PDF page images will appear here after asking questions...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
