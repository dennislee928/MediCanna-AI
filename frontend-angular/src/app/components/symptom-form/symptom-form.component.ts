import { Component, output } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../services/api.service';
import { RecommendationResponse } from '../../models/strain.interface';

const AVOID_EFFECTS_OPTIONS = [
  'Dry Mouth',
  'Dizzy',
  'Anxious',
  'Paranoid',
  'Headache',
  'Dry Eyes',
];

@Component({
  selector: 'app-symptom-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './symptom-form.component.html',
  styleUrl: './symptom-form.component.scss',
})
export class SymptomFormComponent {
  readonly recommendationsReady = output<RecommendationResponse>();
  loading = false;
  errorMessage = '';
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private api: ApiService,
  ) {
    const avoidControls = AVOID_EFFECTS_OPTIONS.map(() => this.fb.control(false));
    this.form = this.fb.group({
      symptoms: [''],
      avoidEffects: this.fb.array(avoidControls),
    });
  }

  get avoidEffects(): FormArray {
    return this.form.get('avoidEffects') as FormArray;
  }

  get avoidOptions(): string[] {
    return AVOID_EFFECTS_OPTIONS;
  }

  onSubmit(): void {
    if (this.loading) return;
    const symptoms = (this.form.get('symptoms')?.value ?? '').trim();
    if (!symptoms) {
      this.errorMessage = '請輸入症狀描述。';
      return;
    }

    const avoid_effects = this.avoidOptions.filter((_, i) => this.avoidEffects.at(i).value);
    this.loading = true;
    this.errorMessage = '';
    this.api.getRecommendations({ symptoms, avoid_effects }).subscribe({
      next: (res) => {
        this.loading = false;
        this.recommendationsReady.emit(res);
      },
      error: (error) => {
        this.loading = false;
        this.errorMessage = error?.error?.error?.message ?? '查詢失敗，請稍後再試。';
      },
    });
  }
}
