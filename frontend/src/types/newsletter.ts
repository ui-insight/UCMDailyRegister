export interface NewsletterSection {
  id: string;
  newsletter_type: 'tdr' | 'myui';
  name: string;
  slug: string;
  display_order: number;
  description: string | null;
  requires_image: boolean;
  image_dimensions: string | null;
  is_active: boolean;
}

export interface Newsletter {
  id: string;
  newsletter_type: 'tdr' | 'myui';
  publish_date: string;
  status: 'draft' | 'in_progress' | 'ready_for_review' | 'submitted' | 'published';
  created_at: string;
  updated_at: string;
}

export interface NewsletterItem {
  id: string;
  newsletter_id: string;
  submission_id: string;
  section_id: string;
  position: number;
  final_headline: string;
  final_body: string;
  run_number: number;
}
