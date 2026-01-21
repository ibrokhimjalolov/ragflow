import { FormContainer } from '@/components/form-container';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Form } from '@/components/ui/form';
import { Textarea } from '@/components/ui/textarea';
import { zodResolver } from '@hookform/resolvers/zod';
import { memo } from 'react';
import { useForm, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { FormWrapper } from '../../components/form-wrapper';
import { useValues } from '../use-values';
import { useWatchFormChange } from '../use-watch-change';

function ServiceAccountJsonField() {
  const { t } = useTranslation();
  const form = useFormContext();
  return (
    <FormField
      control={form.control}
      name="service_account_json"
      render={({ field }) => (
        <FormItem>
          <FormLabel>{t('flow.serviceAccountJson')}</FormLabel>
          <FormControl>
            <Textarea
              {...field}
              placeholder={t('flow.serviceAccountJsonPlaceholder')}
              rows={6}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function GoogleDocsReadForm() {
  const values = useValues();

  const FormSchema = z.object({
    service_account_json: z.string(),
  });

  const form = useForm<z.infer<typeof FormSchema>>({
    defaultValues: values,
    resolver: zodResolver(FormSchema),
  });

  useWatchFormChange(form);

  return (
    <Form {...form}>
      <FormWrapper>
        <FormContainer>
          <ServiceAccountJsonField />
        </FormContainer>
      </FormWrapper>
    </Form>
  );
}

export default memo(GoogleDocsReadForm);
