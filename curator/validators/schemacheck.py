"""Schema checker"""
import logging
import re
from curator.exceptions import ConfigurationError

class SchemaCheck(object):
    def __init__(self, config, schema, test_what, location):
        """
        Validate ``config`` with the provided voluptuous ``schema``.
        ``test_what`` and ``location`` are for reporting the results, in case of
        failure.  If validation is successful, the method returns ``config`` as
        valid.

        :arg config: A configuration dictionary.
        :type config: dict
        :arg schema: A voluptuous schema definition
        :type schema: :class:`voluptuous.schema_builder.Schema`
        :arg test_what: which configuration block is being validated
        :type test_what: str
        :arg location: A string to report which configuration sub-block is being tested.
        :type location: str
        """
        self.loggit = logging.getLogger('curator.validators.SchemaCheck')
        # Set the Schema for validation...
        self.loggit.debug('Schema: %s', schema)
        self.loggit.debug('"%s" config: %s', test_what, config)
        self.config = config
        self.schema = schema
        self.test_what = test_what
        self.location = location
        self.badvalue = None
        self.error = None

    def __parse_error(self):
        """
        Report the error, and try to report the bad key or value as well.
        """
        def get_badvalue(data_string, data):
            elements = re.sub(r'[\'\]]', '', data_string).split('[')
            elements.pop(0) # Get rid of data as the first element
            value = None
            for k in elements:
                try:
                    key = int(k)
                except ValueError:
                    key = k
                if value is None:
                    value = data[key]
                    # if this fails, it's caught below
            return value
        try:
            self.badvalue = get_badvalue(str(self.error).split()[-1], self.config)
        except Exception:
            self.badvalue = '(could not determine)'

    def result(self):
        try:
            return self.schema(self.config)
        except Exception as err:
            try:
                # pylint: disable=E1101
                self.error = err.errors[0]
            except Exception:
                self.error = f'{err}'
            self.__parse_error()
            self.loggit.error('Schema error: %s', self.error)
            raise ConfigurationError(
                f'Configuration: {self.test_what}: Location: {self.location}: Bad Value: '
                f'"{self.badvalue}", {self.error}. Check configuration file.'
            ) from err
