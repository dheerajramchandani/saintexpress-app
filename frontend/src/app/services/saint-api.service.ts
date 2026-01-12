import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpEventType, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SaintApiService {
  private baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  /**
   * Starts a new session.
   * Returns: Observable<{ session_id: string }>
   */
  startSession(): Observable<{ session_id: string }> {
    return this.http.post<{ session_id: string }>(`${this.baseUrl}/session/start`, {})
      .pipe(catchError(this.handleError)) as Observable<{ session_id: string }>;
  }

  /**
   * Uploads a file to a session slot.
   * Returns: Observable<{ uploaded: string }>
   */
  uploadFile(sessionId: string, slot: string, file: File): Observable<{ uploaded: string }> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<{ uploaded: string }>(
      `${this.baseUrl}/session/${encodeURIComponent(sessionId)}/upload/${encodeURIComponent(slot)}`, 
      formData
    ).pipe(catchError(this.handleError));
  }

  /**
   * Runs the session (starts the job).
   * Returns: Observable<any> (metadata or error)
   */
  runSession(sessionId: string): Observable<any> {
    return this.http.post<any>(
      `${this.baseUrl}/session/${encodeURIComponent(sessionId)}/run`, 
      {}
    ).pipe(catchError(this.handleError));
  }

  /**
   * Downloads the result file as blob.
   * Returns: Observable<Blob>
   */
  downloadResult(sessionId: string): Observable<Blob> {
    return this.http.get(
      `${this.baseUrl}/session/${encodeURIComponent(sessionId)}/download`, 
      { responseType: 'blob' }
    ).pipe(catchError(this.handleError));
  }

  /**
   * Deletes the session.
   * Returns: Observable<any>
   */
  deleteSession(sessionId: string): Observable<any> {
    return this.http.delete(
      `${this.baseUrl}/session/${encodeURIComponent(sessionId)}`
    ).pipe(catchError(this.handleError));
  }

  /**
   * Handle HTTP errors gracefully.
   */
  private handleError(error: HttpErrorResponse) {
    if (error.error instanceof ErrorEvent) {
      // Client/network error
      return throwError(() => new Error(`Network error: ${error.error.message}`));
    } else {
      // FastAPI error format or fallback
      const msg = error.error?.detail || error.message || `Server returned code ${error.status}`;
      return throwError(() => new Error(msg));
    }
  }
}
