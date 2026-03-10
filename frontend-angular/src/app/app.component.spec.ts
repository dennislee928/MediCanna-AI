import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { AppComponent } from './app.component';
import { ApiService } from './services/api.service';

class ApiServiceStub {
  getRecommendations() {
    return of({
      recommendations: [],
      meta: { request_id: 'stub', model_version: 'kmeans-v1', warnings: [] },
    });
  }
}

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        { provide: ApiService, useClass: ApiServiceStub },
        provideNoopAnimations(),
      ],
    }).compileComponents();
  });

  it('updates recommendations and meta on callback', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.onRecommendationsReady({
      recommendations: [
        {
          name: 'Alpha',
          type: 'Hybrid',
          rating: 4.4,
          effects: 'Relaxed',
          flavor: 'Sweet',
        },
      ],
      meta: {
        request_id: 'req-100',
        model_version: 'kmeans-v1',
        warnings: ['fallback'],
      },
    });

    expect(component.recommendations.length).toBe(1);
    expect(component.requestId).toBe('req-100');
    expect(component.modelVersion).toBe('kmeans-v1');
    expect(component.warnings).toEqual(['fallback']);
  });
});
