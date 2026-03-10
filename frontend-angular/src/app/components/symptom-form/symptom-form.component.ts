import { Component, output } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../services/api.service';
import { StrainItem } from '../../models/strain.interface';

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
  readonly recommendationsReady = output<StrainItem[]>();
  loading = false;
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
    if (!symptoms) return;

    const avoid_effects = this.avoidOptions.filter((_, i) => this.avoidEffects.at(i).value);
    this.loading = true;
    this.api.getRecommendations({ symptoms, avoid_effects }).subscribe({
      next: (res) => {
        this.loading = false;
        this.recommendationsReady.emit(res.recommendations ?? []);
      },
      error: () => {
        this.loading = false;
        this.recommendationsReady.emit([]);
      },
    });
  }
}
