-- Add enabled_templates column to business_settings table
-- This stores which template IDs are enabled for each business

ALTER TABLE public.business_settings
ADD COLUMN IF NOT EXISTS enabled_templates text[] DEFAULT '{}';

-- Create index for faster array queries
CREATE INDEX IF NOT EXISTS idx_business_settings_enabled_templates
  ON public.business_settings USING GIN (enabled_templates);

-- Add comment for documentation
COMMENT ON COLUMN public.business_settings.enabled_templates IS 'Array of template IDs from Templated.io that are enabled for this business';

-- Example usage:
-- Check if template is enabled: 'template-id' = ANY(enabled_templates)
-- Add template: UPDATE business_settings SET enabled_templates = array_append(enabled_templates, 'template-id')
-- Remove template: UPDATE business_settings SET enabled_templates = array_remove(enabled_templates, 'template-id')
