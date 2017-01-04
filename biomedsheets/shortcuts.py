# -*- coding: utf-8 -*-
"""Python classes for enabling shortcut views on the biomedical sheet

Note that these shortcuts rely on the following assumptions.  These
assumptions are quite strong but make sense in clinical context.  Also, they
enforce a sensible streamlining of the high-throughput biomedical assay
structure which is the case for the interesting studies anyway.

- each shortcut sheet only uses one data type (e.g., WES, WGS, or mass-spec
  data)
- in the case of rare disease studies, only the first active bio and test
  sample and NGS library need to be considered
- in the case of cancer studies, only the first active test sample and NGS
  library are of interesting
- both one and multiple test samples can be of study, e.g., in the case
  of considering multiple parts of a larger tumor or metastesis

This all is to facilitate the automatic processing in pipelines.  Of course,
more assays can be combined by loading the results in a downstream step.
These downstream steps can then combine the information in any fashion they
see fit and build larger, more complex systems out of the simpler building
blocks that this module is meant for.

Also note that none of the shorcut objects will reflect changes in the
underlying schema data structure.
"""

from . import models

__author__ = 'Manuel Holtgrewe <manuel.holtgrewe@bihealth.de>'

#: Token for identifying a rare disease sequencing experiment
RARE_DISEASE = 'rare_disease'
#: Token for identifying a cancer matched tumor/normal study
CANCER_MATCHED = 'cancer_matched'
#: Token for identifying a generic experiment
GENERIC_EXPERIMENT = 'generic_experiment'
#: Known sheet types with shortcuts
SHEET_TYPES = (RARE_DISEASE, CANCER_MATCHED, GENERIC_EXPERIMENT)

#: Key value for "is cancer" flag
KEY_IS_CANCER = 'isCancer'
#: Key value for "extraction type" value
KEY_EXTRACTION_TYPE = 'extractionType'

#: Extraction type "DNA"
EXTRACTION_TYPE_DNA = 'DNA'
#: Extraction type "RNA"
EXTRACTION_TYPE_RNA = 'RNA'

#: Pattern used for the @property def name() functions
NAME_PATTERN = '{pk}-{secondary_id}'

# TODO: the major thing here that is missing in the pre-selection of the
#       part after TestSample, e.g., WES/RNA-seq/WGS library or HPLC-MS


class InvalidSelector(Exception):
    """Raised in the case of an invalid ``TestSample`` child type"""


class MissingDataEntity(Exception):
    """Raised if the given data entity is not known"""


class TestSampleChildShortcut:
    """Helper base class for children of ``TestSampleShortcut``
    """

    def __init__(self, test_sample, wrapped):
        #: Containing ``TestSampleChildShortcut``
        self.test_sample = test_sample
        #: Wrapped raw TestSample child
        self.wrapped = wrapped

    @property
    def pk(self):
        """Shortcut to ``pk`` property of wrapped ``TestSample``

        The value is usually generated by data management system/database.
        """
        return self.wrapped.pk

    @property
    def secondary_id(self):
        """Shortcut to ``secondary_id`` property of wrapped ``TestSample``

        The value is usually assigned by the data generator/customer
        """
        return self.wrapped.secondary_id

    @property
    def name(self):
        """Generate name for test sample, consisting of primary key and
        followed by "path" of secondary ids through sample sheet

        Name of the donor, generated by "${pk}-${secondary_id}"
        """
        return NAME_PATTERN.format(
            pk=str(self.pk).rjust(6, '0'), secondary_id='-'.join([
                self.test_sample.bio_sample.bio_entity.secondary_id,
                self.test_sample.bio_sample.secondary_id,
                self.test_sample.secondary_id,
                self.secondary_id]))

    @property
    def disabled(self):
        """Shortcut to ``disabled`` property of wrapped ``TestSample``"""
        return self.wrapped.disabled

    @property
    def enabled(self):
        """Shortcut to ``enabled`` property of wrapped ``TestSample``"""
        return self.wrapped.enabled


class NGSLibraryShortcut(TestSampleChildShortcut):
    """Shortcut to NGSLibrary
    """

    def __init__(self, test_sample, ngs_library):
        super().__init__(test_sample, ngs_library)
        #: Wrapped raw ``NGSLibrary``
        self.ngs_library = ngs_library


class MSProteinPoolShortcut(TestSampleChildShortcut):
    """Shortcut to MSProteinPool
    """

    def __init__(self, test_sample, ms_protein_pool):
        super().__init__(test_sample, ms_protein_pool)
        #: Wrapped raw ``MSProteinPool``
        self.ms_protein_pool = ms_protein_pool


class TestSampleShortcut:
    """When navigating with the ``biomedsheets.shortcuts`` through the
    sheets, this is the type that you end up instead of raw ``TestSample``
    objects

    Objects of this class are pre-configured with a specific ``TestSample``
    child type (e.g., NGS library or MSProteinPool) where the primary
    active will be picked.
    """

    def __init__(self, bio_sample, test_sample, selector):
        #: Containing shortcut to ``BioSample``
        self.bio_sample = bio_sample
        #: Raw ``TestSample``
        self.test_sample = test_sample
        # Check selector for being valid
        if selector not in models.TEST_SAMPLE_CHILDREN:
            raise InvalidSelector(
                'Invalid test sample selector {}'.format(selector))
        #: Selector for ``TestSample`` children
        self.selector = selector
        #: The selected ``TestSample`` child
        self.assay_sample = self._get_assay_sample()

    @property
    def pk(self):
        """Shortcut to ``pk`` property of wrapped ``TestSample``

        The value is usually generated by data management system/database.
        """
        return self.test_sample.pk

    @property
    def secondary_id(self):
        """Shortcut to ``secondary_id`` property of wrapped ``TestSample``

        The value is usually assigned by the data generator/customer
        """
        return self.test_sample.secondary_id

    @property
    def name(self):
        """Generate name for test sample, consisting of primary key and
        followed by "path" of secondary ids through sample sheet

        Name of the donor, generated by "${pk}-${secondary_id}"
        """
        return NAME_PATTERN.format(
            pk=str(self.pk).rjust(6, '0'), secondary_id='-'.join([
                self.bio_sample.donor.secondary_id,
                self.bio_sample.secondary_id,
                self.secondary_id]))

    @property
    def disabled(self):
        """Shortcut to ``disabled`` property of wrapped ``TestSample``"""
        return self.test_sample.disabled

    @property
    def enabled(self):
        """Shortcut to ``enabled`` property of wrapped ``TestSample``"""
        return self.test_sample.enabled

    def _get_assay_sample(self):
        """Return ``TestSample`` child or raise an exception"""
        values = {
            models.KEY_NGS_LIBRARY: lambda x: x.ngs_libraries.values(),
            models.KEY_MS_PROTEIN_POOL: lambda x: x.ms_protein_pools.values(),
        }
        constructors = {
            models.KEY_NGS_LIBRARY: NGSLibraryShortcut,
            models.KEY_MS_PROTEIN_POOL: MSProteinPoolShortcut,
        }
        attr_lst = values.get(self.selector, lambda x: [])(self.test_sample)
        for entity in attr_lst:
            if not entity.disabled:
                return constructors[self.selector](self, entity)
        raise MissingDataEntity(
            'Could not find data entity for type {} in {}'.format(
                self.selector, self.test_sample))

    def __repr__(self):
        return 'TestSampleShortcut({})'.format(', '.join(map(str, [
            self.test_sample, self.selector, self.assay_sample])))

    def __str__(self):
        return repr(self)


class RareDiseaseCaseSheet:
    """Shortcut for "rare disease" view on bio-medical sample sheets"""

    def __init__(self, sheet):
        #: The wrapped ``Sheet``
        self.sheet = sheet
        # TODO: construct shortcuts into the pedigree


class CancerCaseSheet:
    """Shortcut for "matched tumor/normal" view on bio-medical sample sheets
    """

    def __init__(self, sheet):
        #: The wrapped ``Sheet``
        self.sheet = sheet
        #: List of donors in the sample sheet
        self.donors = list(self._iter_donors())
        #: List of primary matched tumor/normal sample pairs in the sample sheet
        self.primary_sample_pairs = list(self._iter_sample_pairs(True))
        #: List of all matched tumor/normal sample pairs in the sample sheet
        self.all_sample_pairs = list(self._iter_sample_pairs(False))

    def _iter_donors(self):
        """Return iterator over the donors in the study"""
        for bio_entity in self.sheet.bio_entities.values():
            yield CancerDonor(bio_entity)

    def _iter_sample_pairs(self, only_primary_sample_pairs):
        """Return iterator over the matched tumor/normal pairs

        If ``only_primary_sample`` is ``True`` then only one pair per donor
        will be returned with the cancer sample marked as primary.  If this
        flag is ``False`` then one pair for each ``cancer`` sample will be
        returned.
        """
        for donor in self.donors:
            if only_primary_sample_pairs:
                yield donor.primary_pair
            else:
                yield from donor.all_pairs


class CancerDonor:
    """Represent a donor in a matched tumor/normal"""

    def __init__(self, bio_entity):
        #: The ``BioEntity`` from the sample sheet
        self.bio_entity = bio_entity
        #: The primary ``CancerMatchedSamplePair``
        self.primary_pair = self._get_primary_pair()
        #: All tumor/normal pairs
        self.all_pairs = list(self._iter_all_pairs())

    @property
    def pk(self):
        """Shortcut to ``pk`` property of wrapped ``BioEntity``

        The value is usually generated by data management system/database.
        """
        return self.bio_entity.pk

    @property
    def secondary_id(self):
        """Shortcut to ``secondary_id`` property of wrapped ``BioEntity``

        The value is usually assigned by the data generator/customer
        """
        return self.bio_entity.secondary_id

    @property
    def name(self):
        """Generate name for donor, consisting of primary key and followed by
        "path" of secondary ids through sample sheet

        Name of the donor, generated by "${pk}-${secondary_id}"
        """
        return NAME_PATTERN.format(
            pk=str(self.pk).rjust(6, '0'), secondary_id=self.secondary_id)

    @property
    def disabled(self):
        """Shortcut to ``disabled`` property of wrapped ``BioEntity``"""
        return self.bio_entity.disabled

    @property
    def enabled(self):
        """Shortcut to ``enabled`` property of wrapped ``BioEntity``"""
        return self.bio_entity.enabled

    def _get_primary_pair(self):
        """Return primary ``CancerMatchedSamplePair``"""
        return next(self._iter_all_pairs())

    def _iter_all_pairs(self):
        """Iterate all tumor/normal pair"""
        normal_bio_sample = self._get_primary_normal_bio_sample()
        normal_cancer_sample = CancerBioSample(
            self.bio_entity, normal_bio_sample, False)
        for tumor_bio_sample in self._iter_tumor_bio_samples():
            tumor_cancer_sample = CancerBioSample(self.bio_entity,
                tumor_bio_sample, True)
            yield CancerMatchedSamplePair(
                self, tumor_cancer_sample, normal_cancer_sample)

    def _get_primary_normal_bio_sample(self):
        """Return primary normal ``BioSample``

        Raises ``MissingDataEntity`` in the case of problems
        """
        for bio_sample in self.bio_entity.bio_samples.values():
            if KEY_IS_CANCER not in bio_sample.extra_infos:
                raise MissingDataEntity(
                    'Could not find "{}" flag in BioSample {}'.format(
                        KEY_IS_CANCER, bio_sample))
            elif not bio_sample.extra_infos[KEY_IS_CANCER]:
                return bio_sample

        raise MissingDataEntity(
            'Could not find primary normal sample for BioEntity {}'.format(
                self.bio_entity))

    def _iter_tumor_bio_samples(self):
        """Return iterable over all tumor bio samples

        The order depends on the order in ``self.bio_entity.bio_sample``.  If
        the type of this attribute is an ordered dict, then the behaviour of
        this function is reproducible, otherwise it is not.

        Raises ``MissingDataEntity`` in the case of problems
        """
        yielded_any = False
        for bio_sample in self.bio_entity.bio_samples.values():
            if KEY_IS_CANCER not in bio_sample.extra_infos:
                raise MissingDataEntity(
                    'Could not find "{}" flag in BioSample {}'.format(
                        KEY_IS_CANCER, bio_sample))
            elif bio_sample.extra_infos[KEY_IS_CANCER]:
                yielded_any = True
                yield bio_sample
        if not yielded_any:
            raise MissingDataEntity(
                ('Could not find a BioSample with {} = true for '
                 'BioEntity {}'.format(KEY_IS_CANCER, self.bio_entity)))

    def __repr__(self):
        return 'CancerDonor({})'.format(', '.join(map(str, [self.bio_entity])))

    def __str__(self):
        return repr(self)


class CancerMatchedSamplePair:
    """Represents a matched tumor/normal sample pair"""

    def __init__(self, donor, tumor_sample, normal_sample):
        #: The ``BioEntity`` from the sample sheet
        self.donor = donor
        #: Alias for ``self.donor``
        self.bio_entity = self.donor
        #: The ``CancerBioSample`` from the sample sheet
        self.tumor_sample = tumor_sample
        #: The ``CancerBioSample`` from the sample sheet
        self.normal_sample = normal_sample

    def __repr__(self):
        return 'CancerMatchedSamplePair({})'.format(', '.join(
            map(str, [self.donor, self.tumor_sample, self.normal_sample])))

    def __str__(self):
        return repr(self)


class CancerBioSample:
    """Represents one sample in a tumor/normal sample pair in the context
    of a matched Cancer tumor/normal study

    Currently, only NGS samples are supported and at least one DNA library is
    required.  This will change in the future
    """

    def __init__(self, donor, bio_sample, is_cancer):
        #: The ``CancerDonor`` from the sample sheet
        self.donor = donor
        #: Alias to ``CancerDonor``
        self.bio_entity = donor
        #: The ``BioSample`` from the sample sheet
        self.bio_sample = bio_sample
        #: Whether or not the sample is cancer
        self.is_cancer = is_cancer
        #: The primary DNA test sample
        self.dna_test_sample = self._get_primary_dna_test_sample()
        #: The primary RNA test sample, if any
        self.rna_test_sample = self._get_primary_rna_test_sample()
        #: The primary DNA NGS library for this sample
        self.dna_ngs_library = self._get_primary_dna_ngs_library()
        #: The primary RNA NGS library for this sample, if any
        self.rna_ngs_library = self._get_primary_rna_ngs_library()

    @property
    def pk(self):
        """Shortcut to ``pk`` property of wrapped ``BioSample``

        The value is usually generated by data management system/database.
        """
        return self.bio_sample.pk

    @property
    def secondary_id(self):
        """Shortcut to ``secondary_id`` property of wrapped ``BioEntity``

        The value is usually assigned by the data generator/customer
        """
        return self.bio_sample.secondary_id

    @property
    def name(self):
        """Generate name for sample, consisting of primary key and followed by
        "path" of secondary ids through sample sheet

        Name of the donor, generated by "${pk}-${secondary_id}"
        """
        return NAME_PATTERN.format(
            pk=str(self.pk).rjust(6, '0'), secondary_id='-'.join([
                self.donor.secondary_id, self.secondary_id]))

    @property
    def disabled(self):
        """Shortcut to ``disabled`` property of wrapped ``BioEntity``"""
        return self.bio_sample.disabled

    @property
    def enabled(self):
        """Shortcut to ``enabled`` property of wrapped ``BioEntity``"""
        return self.bio_sample.enabled

    def _get_primary_dna_test_sample(self):
        """Spider through ``self.bio_sample`` and return primary DNA test
        sample
        """
        sample = next(self._iter_all_test_samples(EXTRACTION_TYPE_DNA, False))
        return TestSampleShortcut(self, sample, 'ngs_library')

    def _get_primary_rna_test_sample(self):
        """Spider through ``self.bio_sample`` and return primary RNA test
        sample, if any; ``None`` otherwise
        """
        sample = next(self._iter_all_test_samples(EXTRACTION_TYPE_RNA, True),
                      None)
        if sample:
            return TestSampleShortcut(self, sample, 'ngs_library')
        else:
            return None

    def _get_primary_dna_ngs_library(self):
        """Get primary DNA NGS library from self.dna_test_sample
        """
        if not self.dna_test_sample.test_sample.ngs_libraries:
            raise MissingDataEntity(
                'Could not find an DNA NGS library for TestSample {}'.format(
                    self.dna_test_sample.test_sample))
        else:
            return next(iter(self.dna_test_sample.test_sample.ngs_libraries))

    def _get_primary_rna_ngs_library(self):
        """Get primary RNA NGS library from self.rna_test_sample, if any
        """
        if (self.rna_test_sample and
                self.rna_test_sample.test_sample.ngs_libraries):
            return next(iter(self.rna_test_sample.test_sample.ngs_libraries))
        else:
            return None

    def _iter_all_test_samples(self, ext_type, allow_none):
        """Yield all test samples with the given extraction type

        Require yielding of at least one unless ``allow_none``
        """
        yielded_any = False
        for test_sample in self.bio_sample.test_samples.values():
            if KEY_EXTRACTION_TYPE not in test_sample.extra_infos:
                raise MissingDataEntity(
                    'Could not find "{}" flag in TestSample {}'.format(
                        KEY_EXTRACTION_TYPE, test_sample))
            elif test_sample.extra_infos[KEY_EXTRACTION_TYPE] == ext_type:
                yielded_any = True
                yield test_sample
        if not yielded_any and not allow_none:
            raise MissingDataEntity(
                ('Could not find a TestSample with {} == {} for '
                 'BioSample {}'.format(
                     KEY_EXTRACTION_TYPE, ext_type, self.bio_sample)))

    def __repr__(self):
        return 'CancerBioSample({})'.format(', '.join(
            map(str, [self.bio_sample, self.is_cancer])))

    def __str__(self):
        return repr(self)


class GenericExperimentSampleSheet:
    """Shortcut of a generic experiment sample sheet"""

    def __init__(self, sheet):
        #: The wrapped ``Sheet``
        self.sheet = sheet
        #: List of all primary ``TestSample`` of the assumed type
        self.test_samples = list(self._iter_test_samples())

    def _iter_test_samples(self):
        """Iterate over the test samples of the selected type that"""
