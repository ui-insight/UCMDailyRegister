export interface AllowedValue {
  Id: string;
  Value_Group: string;
  Code: string;
  Label: string;
  Display_Order: number;
  Is_Active: boolean;
  Visibility_Role: 'public' | 'staff';
  Description: string | null;
}
