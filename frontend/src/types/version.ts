interface VersionBase {
  id: string;
  version_number: number;
  uploaded_by: string;
  uploaded_at: string;
}

interface FilePayload {
  kind: 'file';
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  link_url: null;
  link_mode: null;
}

interface LinkPayload {
  kind: 'link';
  original_filename: null;
  content_type: null;
  file_size_bytes: null;
  link_url: string;
  link_mode: 'redirect';
}

export type Version = VersionBase & (FilePayload | LinkPayload);

export type PendingVersion = Version & {
  location_slug: string;
  location_display_name: string;
};

export type ArchivedVersion = Version & {
  location_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'superseded';
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
};

export interface ArchiveResponse {
  location_slug: string;
  location_display_name: string;
  versions: ArchivedVersion[];
  total: number;
  page: number;
  per_page: number;
}
