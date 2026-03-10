import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RecommendationListComponent } from './recommendation-list.component';

describe('RecommendationListComponent', () => {
  let fixture: ComponentFixture<RecommendationListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RecommendationListComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(RecommendationListComponent);
  });

  it('renders empty message when no strains', () => {
    fixture.componentRef.setInput('strains', []);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('尚無推薦結果');
  });

  it('renders title when strains exist', () => {
    fixture.componentRef.setInput('strains', [
      {
        name: 'Alpha',
        type: 'Hybrid',
        rating: 4.5,
        effects: 'Relaxed',
        flavor: 'Sweet',
      },
    ]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('推薦品種');
  });
});
