-- Allow AHP as a reserved scenario / run method (engine UI placeholder in app).
ALTER TABLE public.scenarios DROP CONSTRAINT IF EXISTS scenarios_method_type_check;
ALTER TABLE public.scenarios
    ADD CONSTRAINT scenarios_method_type_check
    CHECK (method_type IN ('topsis', 'vft', 'ahp'));

ALTER TABLE public.runs DROP CONSTRAINT IF EXISTS runs_method_check;
ALTER TABLE public.runs
    ADD CONSTRAINT runs_method_check
    CHECK (method IN ('topsis', 'vft', 'ahp'));
