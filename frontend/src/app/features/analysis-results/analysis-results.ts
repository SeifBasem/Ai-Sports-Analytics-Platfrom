import { Component, OnInit } from '@angular/core';
import { AnalysisResult } from '../../models/admin.model';
import { AdminApiService } from '../../services/admin-api.service';

@Component({
  selector: 'app-analysis-results-page',
  standalone: false,
  templateUrl: './analysis-results.html',
  styleUrl: './analysis-results.scss'
})
export class AnalysisResultsPage implements OnInit {
  results: AnalysisResult[] = [];
  selectedResult: AnalysisResult | null = null;

  constructor(private adminData: AdminApiService) { }

  ngOnInit(): void {
    this.adminData.getAnalysisResults().subscribe((results) => {
      this.results = results;
    });
  }

  detectedActionsJson(result: AnalysisResult): string {
    return JSON.stringify(result.detectedActions, null, 2);
  }

  trackByResultId(index: number, result: AnalysisResult): string {
    return result.id;
  }
}
