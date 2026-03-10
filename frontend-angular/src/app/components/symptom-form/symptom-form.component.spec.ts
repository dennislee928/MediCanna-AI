import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { SymptomFormComponent } from './symptom-form.component';
import { ApiService } from '../../services/api.service';
import { RecommendationResponse } from '../../models/strain.interface';

class ApiServiceStub {
  response$ = new Subject<RecommendationResponse>();

  getRecommendations() {
    return this.response$.asObservable();
  }
}

describe('SymptomFormComponent', () => {
  let fixture: ComponentFixture<SymptomFormComponent>;
  let component: SymptomFormComponent;
  let apiService: ApiServiceStub;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SymptomFormComponent],
      providers: [
        { provide: ApiService, useClass: ApiServiceStub },
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SymptomFormComponent);
    component = fixture.componentInstance;
    apiService = TestBed.inject(ApiService) as unknown as ApiServiceStub;
    fixture.detectChanges();
  });

  it('shows validation error when symptoms is blank', () => {
    component.form.patchValue({ symptoms: '   ' });
    component.onSubmit();
    expect(component.errorMessage).toContain('請輸入症狀描述');
  });

  it('emits recommendations and stops loading on success', () => {
    const emitted: RecommendationResponse[] = [];
    component.recommendationsReady.subscribe((value) => emitted.push(value));
    component.form.patchValue({ symptoms: 'pain relief' });
    component.onSubmit();
    expect(component.loading).toBeTrue();

    apiService.response$.next({
      recommendations: [],
      meta: { request_id: 'req-1', model_version: 'kmeans-v1', warnings: [] },
    });

    expect(component.loading).toBeFalse();
    expect(emitted.length).toBe(1);
  });

  it('shows api error message on failure', () => {
    spyOn(TestBed.inject(ApiService), 'getRecommendations').and.returnValue(
      throwError(() => ({ error: { error: { message: 'upstream failure' } } })),
    );
    component.form.patchValue({ symptoms: 'pain relief' });
    component.onSubmit();
    expect(component.errorMessage).toBe('upstream failure');
    expect(component.loading).toBeFalse();
  });

  it('handles immediate observable result', () => {
    spyOn(TestBed.inject(ApiService), 'getRecommendations').and.returnValue(
      of({
        recommendations: [],
        meta: { request_id: 'req-2', model_version: 'kmeans-v1', warnings: [] },
      }),
    );
    component.form.patchValue({ symptoms: 'insomnia' });
    component.onSubmit();
    expect(component.loading).toBeFalse();
  });
});
