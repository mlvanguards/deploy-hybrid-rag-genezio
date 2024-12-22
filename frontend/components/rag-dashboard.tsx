'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Upload, Search, RefreshCw } from 'lucide-react';

const formatFileSize = (bytes) => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

const DocumentCard = ({ document }) => {
  return (
    <Card className="mb-6 bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="text-xl text-slate-100">📄 {document.filename}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-6">
          <div className="space-y-3">
            <h4 className="font-medium text-lg text-slate-100 mb-4">File Details</h4>
            <p className="text-slate-300">Size: {formatFileSize(document.file_size)}</p>
            <p className="text-slate-300">Type: {document.file_type}</p>
            <p className="text-slate-300">Pages: {document.pages.join(', ')}</p>
          </div>
          <div className="space-y-3">
            <h4 className="font-medium text-lg text-slate-100 mb-4">Dates</h4>
            <p className="text-slate-300">Created: {document.creation_date}</p>
            <p className="text-slate-300">Modified: {document.last_modified_date}</p>
          </div>
          <div className="space-y-3">
            <h4 className="font-medium text-lg text-slate-100 mb-4">Storage</h4>
            <p className="text-slate-300">Path: {document.file_path}</p>
          </div>
        </div>

        <div className="mt-6">
          <h4 className="font-medium text-lg text-slate-100 mb-4">Content Previews</h4>
          <div className="space-y-4">
            {document.text_chunks.map((chunk, index) => (
              <div key={index} className="border border-slate-700 rounded-lg p-6 bg-slate-800">
                <p className="font-medium text-slate-100 mb-3">Page {chunk.page}</p>
                <p className="text-slate-300">{chunk.text}</p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const RAGDashboard = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [numResults, setNumResults] = useState(5);
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleFileChange = (event) => {
    setFiles(Array.from(event.target.files));
  };

  const handleUpload = async () => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));

      const response = await fetch(' http://localhost:53232/index', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      setFiles([]);
      setActiveTab('documents');
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const params = new URLSearchParams({
        query: searchQuery,
      });

      const response = await fetch(`http://localhost:53232/search?${params}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const results = await response.json();
      setSearchResults(results.response);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="container mx-auto p-8">
        <h1 className="text-4xl font-bold mb-8">📚 Genezio RAG</h1>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="mb-6 bg-slate-900">
            <TabsTrigger value="upload" className="text-lg">Upload Documents</TabsTrigger>
            <TabsTrigger value="search" className="text-lg">Search</TabsTrigger>
          </TabsList>

          <TabsContent value="upload">
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="pt-8">
                <Input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handleFileChange}
                  className="mb-6 bg-slate-800 border-slate-700 text-slate-100"
                />

                {files.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-medium text-lg text-slate-100 mb-4">Selected files:</h3>
                    {files.map((file, index) => (
                      <p key={index} className="text-slate-300">📄 {file.name}</p>
                    ))}
                  </div>
                )}

                <Button
                  onClick={handleUpload}
                  disabled={!files.length || isProcessing}
                  className="bg-blue-600 hover:bg-blue-700 text-lg h-12"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-5 w-5" />
                      Process and Index Documents
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="search">
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="pt-8">
                <div className="space-y-6">
                  <Input
                    placeholder="Enter your search query"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-800 border-slate-700 text-slate-100 text-lg h-12"
                  />

                  <div>
                    <p className="text-lg mb-4 text-slate-300">Number of results: {numResults}</p>
                    <Slider
                      value={[numResults]}
                      onValueChange={([value]) => setNumResults(value)}
                      min={1}
                      max={20}
                      step={1}
                      className="py-4"
                    />
                  </div>

                  <Button
                    onClick={handleSearch}
                    disabled={!searchQuery.trim() || isSearching}
                    className="bg-blue-600 hover:bg-blue-700 text-lg h-12"
                  >
                    {isSearching ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Search className="mr-2 h-5 w-5" />
                        Search
                      </>
                    )}
                  </Button>

                  {searchResults && (
                    <div className="mt-8">
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="pt-6">
                          <p className="text-slate-300 whitespace-pre-wrap">{searchResults}</p>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default RAGDashboard;