import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = "https://ipbpjbwfqwjqhtxgaohw.supabase.co"; 
const SUPABASE_ANON_KEY = "sb_publishable_7ptqRADjLSc9M6KFbbZdiA_qIR4t_K1";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);