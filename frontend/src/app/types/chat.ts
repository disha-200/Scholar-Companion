export interface Citation {
    page: number;
    textSnippet: string;
  }
  
  export interface ChatResponse {
    answer: string;
    citations: Citation[];
  }
  