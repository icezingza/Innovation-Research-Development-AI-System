export interface CoordinatedResult {
  session_id: string;
  goal: string;
  sub_questions: string[];
  hypotheses: Record<string, any>[];
  critiques: Record<string, any>[];
  synthesis: Record<string, any>;
  duration_seconds: number;
  events_published: number;
}

export interface HypothesisRecord {
  question: string;
  statement: string;
  [key: string]: any;
}

export interface ReasoningTrace {
  id: string;
  step: string;
  thought: string;
  timestamp: string;
}

export interface WorkflowStatus {
  session_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_step: string;
  progress: number;
}
