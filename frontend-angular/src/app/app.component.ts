import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SymptomFormComponent } from './components/symptom-form/symptom-form.component';
import { RecommendationListComponent } from './components/recommendation-list/recommendation-list.component';
import { StrainItem } from './models/strain.interface';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, SymptomFormComponent, RecommendationListComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'MediCanna AI';
  recommendations: StrainItem[] = [];

  onRecommendationsReady(strains: StrainItem[]): void {
    this.recommendations = strains;
  }
}
