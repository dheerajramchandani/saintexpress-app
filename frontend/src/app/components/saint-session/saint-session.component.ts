import { Component } from '@angular/core';
import { SaintApiService } from '../../services/saint-api.service';

@Component({
  selector: 'app-root',
  templateUrl: './saint-session.component.html',
  styleUrls: ['./saint-session.component.css']
})
export class SaintSessionComponent {
  sessionId: string | null = null;
  fileNames: { [slot: string]: string | null } = { interaction: null, prey: null, bait: null };
  files: { [slot: string]: File | null } = { interaction: null, prey: null, bait: null };
  uploadedSlots: Set<string> = new Set();

  running = false;
  runSuccess = false;
  errorMsg: string | null = null;
  canDownload = false;

  constructor(private api: SaintApiService) {}
//   constructor() {
//     console.log("SaintSessionComponent Constructed");
//   }

  startSession() {
    this.resetUI();
    this.api.startSession().subscribe({
      next: res => {
        this.sessionId = res.session_id;
      },
      error: err => {
        this.errorMsg = err.message;
      }
    });
  }

  onFileSelected(event: any, slot: string) {
    const file = event.target.files[0];
    if (!file) return;
    this.fileNames[slot] = file.name;
    this.files[slot] = file;
    if (this.sessionId) {
      this.api.uploadFile(this.sessionId, slot, file).subscribe({
        next: _ => {
          this.uploadedSlots.add(slot);
          // File re-upload: just overwrite slot
        },
        error: err => {
          this.errorMsg = err.message;
        }
      });
    }
  }

  canRun(): boolean {
    return this.sessionId != null && this.uploadedSlots.size === 3 && !this.running;
  }

  runProcess() {
    if (!this.sessionId) return;
    this.running = true;
    this.runSuccess = false;
    this.errorMsg = null;
    this.canDownload = false;
    this.api.runSession(this.sessionId).subscribe({
      next: res => {
        if (res.success) {
          this.runSuccess = true;
          this.canDownload = true;
        } else {
          // Defensive: error branch
          this.errorMsg = res.stderr || 'Process failed';
        }
        this.running = false;
      },
      error: err => {
        const startIndex = err.message.indexOf('terminate called after');
        this.errorMsg = startIndex >= 0 ? err.message.substring(startIndex) : err.message;
        this.errorMsg = "ATTENTION! Error: " + this.errorMsg;
        this.running = false;
      }
    });
  }

  downloadResult() {
    if (!this.sessionId) return;
    this.api.downloadResult(this.sessionId).subscribe({
      next: blob => {
        // Use default output file name as per backend (list.txt or meta)
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'list.txt';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      },
      error: err => {
        this.errorMsg = err.message;
      }
    });
  }

  deleteSession() {
    if (!this.sessionId) return;
    this.api.deleteSession(this.sessionId).subscribe({
      next: () => this.resetUI(),
      error: err => {
        this.errorMsg = err.message;
      }
    });
  }

  resetUI() {
    this.sessionId = null;
    this.fileNames = { interaction: null, prey: null, bait: null };
    this.files = { interaction: null, prey: null, bait: null };
    this.uploadedSlots.clear();
    this.running = false;
    this.runSuccess = false;
    this.errorMsg = null;
    this.canDownload = false;
  }
}
