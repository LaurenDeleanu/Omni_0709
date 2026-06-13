// Dummy SMTP integration module
// Provides placeholder implementations for Zoho, Gmail, and Outlook SMTP services.

export interface SmtpClient {
  sendMail(to: string, subject: string, body: string): Promise<void>;
}

export class ZohoSmtpClient implements SmtpClient {
  async sendMail(to: string, subject: string, body: string): Promise<void> {
    // Dummy implementation – in real code, integrate with Zoho SMTP API.
    console.log(`[Zoho] Sending email to ${to} with subject "${subject}"`);
  }
}

export class GmailSmtpClient implements SmtpClient {
  async sendMail(to: string, subject: string, body: string): Promise<void> {
    // Dummy implementation – in real code, integrate with Gmail SMTP.
    console.log(`[Gmail] Sending email to ${to} with subject "${subject}"`);
  }
}

export class OutlookSmtpClient implements SmtpClient {
  async sendMail(to: string, subject: string, body: string): Promise<void> {
    // Dummy implementation – in real code, integrate with Outlook SMTP.
    console.log(`[Outlook] Sending email to ${to} with subject "${subject}"`);
  }
}

// Export a factory for convenience
export function createSmtpClient(provider: 'zoho' | 'gmail' | 'outlook'): SmtpClient {
  switch (provider) {
    case 'zoho':
      return new ZohoSmtpClient();
    case 'gmail':
      return new GmailSmtpClient();
    case 'outlook':
      return new OutlookSmtpClient();
    default:
      throw new Error(`Unsupported provider: ${provider}`);
  }
}
